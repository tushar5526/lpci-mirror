# Copyright 2021-2022 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

import fnmatch
import io
import itertools
import json
import os
import shlex
from argparse import ArgumentParser, Namespace
from pathlib import Path, PurePath
from tempfile import NamedTemporaryFile
from typing import Dict, List, Optional, Set

import yaml
from craft_cli import BaseCommand, EmitterMode, emit
from craft_providers import Executor, lxd
from craft_providers.actions.snap_installer import install_from_store
from dotenv import dotenv_values
from jinja2 import BaseLoader, Environment
from pluggy import PluginManager

from lpcraft import env
from lpcraft.config import Config, Input, Job, Output
from lpcraft.errors import CommandError
from lpcraft.plugin.manager import get_plugin_manager
from lpcraft.plugins import PLUGINS
from lpcraft.providers import Provider, get_provider
from lpcraft.utils import get_host_architecture


def _check_relative_path(path: PurePath, container: PurePath) -> PurePath:
    """Check that `path` does not escape `container`.

    Any symlinks in `path` must already have been resolved within the
    context of the container.

    :raises CommandError: if `path` is outside `container` when fully
        resolved.
    :return: A version of `path` relative to `container`.
    """
    try:
        return path.relative_to(container)
    except ValueError as e:
        raise CommandError(str(e), retcode=1)


def _convert_config_list_to_dict(list_: List[str]) -> Dict[str, str]:
    # takes a list of strings, each string separated by an equal sign,
    # and converts it to a dictionary
    return dict(pair.split("=", maxsplit=1) for pair in list_)


def _remove_prefix_if_possible(path: PurePath, prefix: str) -> PurePath:
    """Remove an initial prefix from `path` if possible.

    This is useful for paths that are normally within the build tree, but
    may optionally escape to the parent directory of the build tree (and no
    further).  For the purpose of copying files to the output directory,
    paths within the build tree should be made relative to the build tree
    and preserve any subdirectory structure there, but paths in the parent
    directory should be relative to the parent directory.

    `_copy_output_paths` recursively lists files within the parent directory
    of the build tree, and uses this to ensure that those paths which are
    within the build tree itself are made relative to the build tree.
    """
    try:
        return path.relative_to(prefix)
    except ValueError:
        return path


def _list_files(instance: Executor, path: Path) -> List[PurePath]:
    """Find entries in `path` on `instance`.

    :param instance: Provider instance to search.
    :param path: Path to directory to search.
    :return: List of non-directory paths found, relative to `path`.
    """
    cmd = ["find", str(path), "-mindepth", "1"]
    # Exclude directories.
    cmd.extend(["!", "-type", "d"])
    # Produce unambiguous output: file name relative to the starting path,
    # terminated by NUL.
    cmd.extend(["-printf", "%P\\0"])
    paths = (
        instance.execute_run(cmd, capture_output=True, check=True)
        .stdout.rstrip(b"\0")
        .split(b"\0")
    )
    return [PurePath(os.fsdecode(p)) for p in paths]


def _resolve_symlinks(
    instance: Executor, paths: List[PurePath]
) -> List[PurePath]:
    """Resolve symlinks in each of `paths` on `instance`.

    Similar to `Path.resolve`, but doesn't require a Python process on
    `instance`.

    :param instance: Provider instance to inspect.
    :param paths: Paths to dereference.
    :return: Dereferenced version of each of the input paths.
    """
    paths = (
        instance.execute_run(
            ["readlink", "-f", "-z", "--"] + [str(path) for path in paths],
            capture_output=True,
            check=True,
        )
        .stdout.rstrip(b"\0")
        .split(b"\0")
    )
    return [PurePath(os.fsdecode(p)) for p in paths]


def _copy_input_paths(
    input: Input, remote_cwd: Path, instance: Executor, output_path: Path
) -> None:
    """Copy designated input artifacts into a job."""
    source_parent_path = output_path / input.job_name
    source_jobs = (
        list(source_parent_path.iterdir())
        if source_parent_path.exists()
        else []
    )
    if not source_jobs:
        raise CommandError(
            f"Requested input from {input.job_name!r}, but that job was not "
            f"previously executed or did not produce any output artifacts."
        )
    elif len(source_jobs) > 1:
        raise CommandError(
            f"Requested input from {input.job_name!r}, but more than one job "
            f"with that name was previously executed and produced output "
            f"artifacts in the following paths: {source_jobs!r}."
        )
    source_path = source_jobs[0]

    [target_path] = _resolve_symlinks(
        instance, [remote_cwd / input.target_directory]
    )
    _check_relative_path(target_path, remote_cwd)

    paths = []
    for dirpath, _, filenames in os.walk(source_path / "files"):
        paths.extend(
            [
                Path(dirpath).relative_to(source_path / "files") / filename
                for filename in filenames
            ]
        )
    paths = sorted(paths)
    parent_paths = sorted(set(path.parent for path in paths) | {Path(".")})

    try:
        instance.execute_run(
            ["mkdir", "-p"]
            + [str(target_path / "files" / path) for path in parent_paths],
            check=True,
        )
        for path in paths:
            instance.push_file(
                source=source_path / "files" / path,
                # Path() here works around
                # https://github.com/canonical/craft-providers/pull/135.
                destination=Path(target_path / "files" / path),
            )
        instance.push_file(
            source=source_path / "properties",
            # Path() here works around
            # https://github.com/canonical/craft-providers/pull/135.
            destination=Path(target_path / "properties"),
        )
    except Exception as e:
        raise CommandError(str(e), retcode=1)


def _copy_output_paths(
    output: Output, remote_cwd: Path, instance: Executor, target_path: Path
) -> None:
    """Copy designated output paths from a completed job."""
    if output.paths is None:
        return

    for path_pattern in output.paths:
        # We'll also check individual glob expansions, but checking the
        # pattern as a whole first produces clearer error messages.  We have
        # to use os.path for this, as pathlib doesn't expose any equivalent
        # of normpath.
        _check_relative_path(
            PurePath(os.path.normpath(remote_cwd / path_pattern)),
            remote_cwd.parent,
        )

    remote_paths = sorted(_list_files(instance, remote_cwd.parent))
    output_files = target_path / "files"

    filtered_paths: Set[PurePath] = set()
    for path_pattern in output.paths:
        # We listed the parent of the build tree in order to allow
        # output.paths to reference the parent directory.  The patterns are
        # still relative to the build tree, though, so make our paths
        # relative to the build tree again so that they can be matched
        # properly.
        paths = [
            os.path.relpath(path, remote_cwd.name) for path in remote_paths
        ]
        result = fnmatch.filter(paths, path_pattern)
        if not result:
            raise CommandError(
                f"{path_pattern} has not matched any output files."
            )
        for name in result:
            filtered_paths.add(PurePath(name))

    resolved_paths = _resolve_symlinks(
        instance,
        [remote_cwd / path for path in sorted(filtered_paths)],
    )

    for path in sorted(resolved_paths):
        relative_path = _remove_prefix_if_possible(
            _check_relative_path(path, remote_cwd.parent), remote_cwd.name
        )
        destination = output_files / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            # Path() here works around
            # https://github.com/canonical/craft-providers/pull/83.
            instance.pull_file(source=Path(path), destination=destination)
        except Exception as e:
            raise CommandError(str(e), retcode=1)


def _copy_output_properties(
    output: Output, remote_cwd: Path, instance: Executor, target_path: Path
) -> None:
    """Copy designated output properties from a completed job."""
    properties = dict(output.properties or {})

    if output.dynamic_properties:
        [path] = _resolve_symlinks(
            instance,
            [remote_cwd / output.dynamic_properties],
        )
        _check_relative_path(path, remote_cwd)
        dynamic_properties = dotenv_values(
            stream=io.StringIO(
                instance.execute_run(
                    ["cat", str(path)],
                    capture_output=True,
                    text=True,
                ).stdout
            )
        )
        for key, value in dynamic_properties.items():
            if value is not None:
                properties[key] = value
            else:
                properties.pop(key, None)

    with open(target_path / "properties", "w") as f:
        json.dump(properties, f)


def _resolve_runtime_value(
    pm: PluginManager, job: Job, hook_name: str, job_property: str
) -> Optional[str]:
    command_value: Optional[str] = None
    command_from_config = getattr(job, job_property)
    plugin: Optional[str] = getattr(job, "plugin", None)
    interpolated_run_command = False
    if plugin is not None and plugin in PLUGINS:
        interpolated_run_command = PLUGINS[plugin].INTERPOLATES_RUN_COMMAND
    if command_from_config is not None and not interpolated_run_command:
        command_value = command_from_config
    else:
        rv = getattr(pm.hook, hook_name)()
        command_value = next(iter(rv), None)
    return command_value


def _install_apt_packages(
    job_name: str,
    job: Job,
    packages: List[str],
    instance: lxd.LXDInstance,
    host_architecture: str,
    remote_cwd: Path,
    replace_package_repositories: Optional[List[str]],
    package_repositories: List[str],
    environment: Optional[Dict[str, Optional[str]]],
    secrets: Optional[Dict[str, str]],
) -> None:
    if replace_package_repositories or package_repositories:
        sources_list_path = "/etc/apt/sources.list"

        with NamedTemporaryFile(mode="w+") as tmpfile:
            try:
                instance.pull_file(
                    source=Path(sources_list_path),
                    destination=Path(tmpfile.name),
                )
            except Exception as e:
                raise CommandError(str(e), retcode=1)
            sources = tmpfile.read()

        if replace_package_repositories:
            sources = "\n".join(replace_package_repositories) + "\n"
        if package_repositories:
            sources += "\n" + "\n".join(package_repositories)
            if secrets:
                template = Environment(loader=BaseLoader()).from_string(
                    sources
                )
                sources = template.render(**secrets)
            sources += "\n"

        with emit.open_stream("Replacing /etc/apt/sources.list") as stream:
            instance.push_file_io(
                destination=PurePath(sources_list_path),
                content=io.BytesIO(sources.encode()),
                file_mode="0644",
                group="root",
                user="root",
            )

    # update local repository information
    apt_update = ["apt", "update"]
    with emit.open_stream(f"Running {apt_update}") as stream:
        proc = instance.execute_run(
            apt_update,
            cwd=remote_cwd,
            env=environment,
            stdout=stream,
            stderr=stream,
        )
    if proc.returncode != 0:
        raise CommandError(
            f"Job {job_name!r} for "
            f"{job.series}/{host_architecture} failed with "
            f"exit status {proc.returncode} "
            f"while running `{shlex.join(apt_update)}`.",
            retcode=proc.returncode,
        )
    packages_cmd = ["apt", "install", "-y"] + packages
    emit.progress("Installing system packages")
    with emit.open_stream(f"Running {packages_cmd}") as stream:
        proc = instance.execute_run(
            packages_cmd,
            cwd=remote_cwd,
            env=environment,
            stdout=stream,
            stderr=stream,
        )
    if proc.returncode != 0:
        raise CommandError(
            f"Job {job_name!r} for "
            f"{job.series}/{host_architecture} failed with "
            f"exit status {proc.returncode} "
            f"while running `{shlex.join(packages_cmd)}`.",
            retcode=proc.returncode,
        )


def _run_instance_command(
    command: str,
    job_name: str,
    job: Job,
    instance: lxd.LXDInstance,
    host_architecture: str,
    remote_cwd: Path,
    environment: Optional[Dict[str, Optional[str]]],
) -> None:
    full_run_cmd = ["bash", "--noprofile", "--norc", "-ec", command]
    emit.progress("Running command for the job...")
    original_mode = emit.get_mode()
    if original_mode == EmitterMode.BRIEF:
        emit.set_mode(EmitterMode.VERBOSE)
    with emit.open_stream(f"Running {full_run_cmd}") as stream:
        proc = instance.execute_run(
            full_run_cmd,
            cwd=remote_cwd,
            env=environment,
            stdout=stream,
            stderr=stream,
        )
    if original_mode == EmitterMode.BRIEF:
        emit.set_mode(original_mode)
    if proc.returncode != 0:
        raise CommandError(
            f"Job {job_name!r} for "
            f"{job.series}/{host_architecture} failed with "
            f"exit status {proc.returncode}.",
            retcode=proc.returncode,
        )


def _run_job(
    config: Config,
    job_name: str,
    job_index: int,
    provider: Provider,
    output: Optional[Path],
    replace_package_repositories: Optional[List[str]],
    package_repositories: List[str],
    env_from_cli: Optional[List[str]] = None,
    plugin_settings: Optional[List[str]] = None,
    secrets: Optional[Dict[str, str]] = None,
) -> None:
    """Run a single job."""
    # XXX jugmac00 2022-04-27: we should create a configuration object to be
    # passed in and not so many arguments
    job = config.jobs[job_name][job_index]
    host_architecture = get_host_architecture()
    if host_architecture not in job.architectures:
        return
    # verbosity is necessary to please mypy
    if plugin_settings is not None:
        plugin_settings_as_dict = _convert_config_list_to_dict(plugin_settings)
        pm = get_plugin_manager(job, plugin_settings_as_dict)
    else:
        pm = get_plugin_manager(job, None)
    pre_run_command = _resolve_runtime_value(
        pm,
        job,
        hook_name="lpcraft_execute_before_run",
        job_property="run_before",
    )
    run_command = _resolve_runtime_value(
        pm,
        job,
        hook_name="lpcraft_execute_run",
        job_property="run",
    )
    post_run_command = _resolve_runtime_value(
        pm,
        job,
        hook_name="lpcraft_execute_after_run",
        job_property="run_after",
    )

    if not run_command:
        raise CommandError(
            f"Job {job_name!r} for {job.series}/{host_architecture} "
            f"does not set 'run'"
        )

    # XXX jugmac00 2021-12-17: extract inferring environment variables
    rv = pm.hook.lpcraft_set_environment()
    if rv:
        # XXX jugmac00 2021-12-17: check for length or reduce?
        env_from_plugin = rv[0]
    else:
        env_from_plugin = {}

    env_from_configuration = job.environment
    if env_from_configuration is not None:
        env_from_plugin.update(env_from_configuration)
    environment = env_from_plugin
    if env_from_cli:
        # XXX jugmac00 2022-05-13: use _convert_config_list_to_dict
        pairs_from_cli = dict(
            pair.split("=", maxsplit=1) for pair in env_from_cli
        )
        environment.update(pairs_from_cli)

    cwd = Path.cwd()
    remote_cwd = env.get_managed_environment_project_path()

    emit.progress(
        f"Launching environment for {job.series}/{host_architecture}"
    )
    with provider.launched_environment(
        project_name=cwd.name,
        project_path=cwd,
        series=job.series,
        architecture=host_architecture,
    ) as instance:
        snaps = list(itertools.chain(*pm.hook.lpcraft_install_snaps()))
        for snap in snaps:
            emit.progress(f"Running `snap install {snap}`")
            install_from_store(
                executor=instance,
                snap_name=snap,
                channel="latest/stable",
                classic=True,
            )
        packages = list(itertools.chain(*pm.hook.lpcraft_install_packages()))
        if packages:
            _install_apt_packages(
                job_name=job_name,
                job=job,
                packages=packages,
                instance=instance,
                host_architecture=host_architecture,
                remote_cwd=remote_cwd,
                replace_package_repositories=replace_package_repositories,
                package_repositories=package_repositories,
                environment=environment,
                secrets=secrets,
            )

        if job.input is not None and output is not None:
            _copy_input_paths(job.input, remote_cwd, instance, output)

        for cmd in (pre_run_command, run_command, post_run_command):
            if cmd:
                _run_instance_command(
                    command=cmd,
                    job_name=job_name,
                    job=job,
                    instance=instance,
                    host_architecture=host_architecture,
                    remote_cwd=remote_cwd,
                    environment=environment,
                )
        if config.license:
            if not job.output:
                job.output = Output()
            # XXX cjwatson 2022-08-09: Consider adding a default value for
            # `Output.properties` instead.
            if job.output.properties is None:
                job.output.properties = dict()
            values = config.license.dict()
            # workaround necessary to please mypy
            assert isinstance(job.output.properties, dict)
            for key, value in values.items():
                if "license" not in job.output.properties:
                    job.output.properties["license"] = dict()
                job.output.properties["license"][key] = value

        if job.output is not None and output is not None:
            target_path = output / job_name / str(job_index)
            target_path.mkdir(parents=True, exist_ok=True)
            _copy_output_paths(job.output, remote_cwd, instance, target_path)
            _copy_output_properties(
                job.output, remote_cwd, instance, target_path
            )


def _get_job_instance_name(provider: Provider, job: Job) -> str:
    """Return the instance name for the given provider and job."""
    cwd = Path.cwd()
    return provider.get_instance_name(
        project_name=cwd.name,
        project_path=cwd,
        series=job.series,
        architecture=get_host_architecture(),
    )


class RunCommand(BaseCommand):
    """Run a pipeline, launching managed environments as needed."""

    name = "run"
    help_msg = __doc__.splitlines()[0]
    overview = __doc__
    common = True

    def fill_parser(self, parser: ArgumentParser) -> None:
        """Add arguments specific to this command."""
        parser.add_argument(
            "--output-directory",
            type=Path,
            help="Write output files to this directory.",
        )
        parser.add_argument(
            "-c",
            "--config",
            type=Path,
            default=".launchpad.yaml",
            help="Read the configuration file from this path.",
        )
        parser.add_argument(
            "--clean",
            action="store_true",
            default=False,
            help=(
                "Clean the managed environments created "
                "for the pipeline after the running it."
            ),
        )
        # Job configuration options.
        parser.add_argument(
            "--apt-replace-repositories",
            action="append",
            default=[],
            help="(deprecated) Overwrite /etc/apt/sources.list.",
        )
        parser.add_argument(
            "--replace-package-repositories",
            action="append",
            default=[],
            help="Overwrite /etc/apt/sources.list.",
        )
        parser.add_argument(
            "--plugin-setting",
            action="append",
            help="Add additional plugin setting.",
        )
        parser.add_argument(
            "--set-env",
            action="append",
            help="Set an environment variable.",
        )
        parser.add_argument(
            "--secrets",
            dest="secrets_file",
            metavar="file",
            default=None,
            type=Path,
            help="Pass in a YAML-based configuration file for secrets.",
        )
        parser.add_argument(
            "--package-repository",
            action="append",
            default=[],
            dest="package_repositories",
            help="Provide an additional package repository.",
        )

    def run(self, args: Namespace) -> int:
        """Run the command."""
        if getattr(args, "apt_replace_repositories"):
            emit.message(
                "Warning: `--apt-replace-repositories` is deprecated - "
                "Please use `--replace-package-repositories instead"
            )
        config = Config.load(args.config)

        provider = get_provider()
        provider.ensure_provider_is_available()

        secrets = {}
        if args.secrets_file:
            with open(args.secrets_file) as f:
                content = f.read()
            secrets = yaml.safe_load(content)
        for stage in config.pipeline:
            stage_failed = False
            for job_name in stage:
                try:
                    jobs = config.jobs.get(job_name, [])
                    if not jobs:
                        raise CommandError(
                            f"No job definition for {job_name!r}"
                        )
                    for job_index, job in enumerate(jobs):
                        # we prefer package repositories via CLI more
                        # so they need to come first
                        # also see sources.list(5)
                        package_repositories = args.package_repositories
                        for group in job.package_repositories:
                            for repository in group.sources_list_lines():
                                package_repositories.append(repository)
                        _run_job(
                            config,
                            job_name,
                            job_index,
                            provider,
                            args.output_directory,
                            replace_package_repositories=(
                                args.apt_replace_repositories
                                + args.replace_package_repositories
                            ),
                            package_repositories=package_repositories,
                            env_from_cli=args.set_env,
                            plugin_settings=args.plugin_setting,
                            secrets=secrets,
                        )

                except CommandError as e:
                    if len(stage) == 1:
                        # Single-job stage, so just reraise this
                        # in order to get simpler error messages.
                        raise
                    else:
                        emit.error(e)
                        stage_failed = True
                finally:
                    if args.clean:
                        cwd = Path.cwd()
                        provider.clean_project_environments(
                            project_name=cwd.name,
                            project_path=cwd,
                            instances=[
                                _get_job_instance_name(provider, job),
                            ],
                        )
            if stage_failed:
                raise CommandError(
                    f"Some jobs in {stage} failed; stopping.", retcode=1
                )
        return 0


class RunOneCommand(BaseCommand):
    """Select and run a single job from a pipeline.

    (This command is for use by Launchpad, and is subject to change.)
    """

    name = "run-one"
    help_msg = __doc__.splitlines()[0]
    overview = __doc__
    hidden = True

    def fill_parser(self, parser: ArgumentParser) -> None:
        """Add arguments specific to this command."""
        parser.add_argument(
            "--output-directory",
            type=Path,
            help="Write output files to this directory.",
        )
        parser.add_argument(
            "-c",
            "--config",
            type=Path,
            default=".launchpad.yaml",
            help="Read the configuration file from this path.",
        )
        parser.add_argument(
            "--clean",
            action="store_true",
            default=False,
            help=(
                "Clean the managed environment created for the job "
                "after running it."
            ),
        )
        parser.add_argument("job", help="Run only this job name.")
        parser.add_argument(
            "index",
            type=int,
            metavar="N",
            help="Run only the Nth job with the given name (indexing from 0).",
        )
        # Job configuration options.
        parser.add_argument(
            "--apt-replace-repositories",
            action="append",
            default=[],
            help="(deprecated) Overwrite /etc/apt/sources.list.",
        )
        parser.add_argument(
            "--replace-package-repositories",
            action="append",
            default=[],
            help="Overwrite /etc/apt/sources.list.",
        )
        parser.add_argument(
            "--plugin-setting",
            action="append",
            help="Add additional plugin setting.",
        )
        parser.add_argument(
            "--set-env",
            action="append",
            help="Set an environment variable.",
        )
        parser.add_argument(
            "--secrets",
            dest="secrets_file",
            metavar="file",
            default=None,
            type=Path,
            help="Pass in a YAML-based configuration file for secrets.",
        )
        parser.add_argument(
            "--package-repository",
            action="append",
            default=[],
            dest="package_repositories",
            help="Provide an additional package repository.",
        )

    def run(self, args: Namespace) -> int:
        """Run the command."""
        if getattr(args, "apt_replace_repositories"):
            emit.message(
                "Warning: `--apt-replace-repositories` is deprecated - "
                "Please use `--replace-package-repositories instead"
            )
        config = Config.load(args.config)

        jobs = config.jobs.get(args.job, [])
        if not jobs:
            raise CommandError(f"No job definition for {args.job!r}")
        if args.index >= len(jobs):
            raise CommandError(
                f"No job definition with index {args.index} for {args.job!r}"
            )
        job = jobs[args.index]

        provider = get_provider()
        provider.ensure_provider_is_available()

        secrets = {}
        if args.secrets_file:
            with open(args.secrets_file) as f:
                content = f.read()
            secrets = yaml.safe_load(content)
        # we prefer package repositories via CLI more
        # so they need to come first
        # also see sources.list(5)
        package_repositories = args.package_repositories
        for group in job.package_repositories:
            for repository in group.sources_list_lines():
                package_repositories.append(repository)
        try:
            _run_job(
                config,
                args.job,
                args.index,
                provider,
                args.output_directory,
                replace_package_repositories=(
                    args.apt_replace_repositories
                    + args.replace_package_repositories
                ),
                package_repositories=package_repositories,
                env_from_cli=args.set_env,
                plugin_settings=args.plugin_setting,
                secrets=secrets,
            )
        finally:
            if args.clean:
                cwd = Path.cwd()
                provider.clean_project_environments(
                    project_name=cwd.name,
                    project_path=cwd,
                    instances=[_get_job_instance_name(provider, job)],
                )

        return 0
