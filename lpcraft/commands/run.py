# Copyright 2021-2022 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

import fnmatch
import io
import itertools
import json
import os
import shlex
from argparse import Namespace
from pathlib import Path, PurePath
from typing import Dict, List, Optional, Set

from craft_cli import EmitterMode, emit
from craft_providers import Executor, lxd
from craft_providers.actions.snap_installer import install_from_store
from dotenv import dotenv_values
from pluggy import PluginManager

from lpcraft import env
from lpcraft.config import Config, Job, Output
from lpcraft.errors import CommandError
from lpcraft.plugin.manager import get_plugin_manager
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
    command_from_config = getattr(job, job_property)
    if command_from_config is not None:
        return command_from_config
    rv = getattr(pm.hook, hook_name)()
    return next(iter(rv), None)


def _install_apt_packages(
    job_name: str,
    job: Job,
    packages: List[str],
    instance: lxd.LXDInstance,
    host_architecture: str,
    remote_cwd: Path,
    apt_replacement_repositories: Optional[List[str]],
    environment: Optional[Dict[str, Optional[str]]],
) -> None:
    if apt_replacement_repositories:
        # replace sources.list
        lines = "\n".join(apt_replacement_repositories) + "\n"
        with emit.open_stream("Replacing /etc/apt/sources.list") as stream:
            instance.push_file_io(
                destination=PurePath("/etc/apt/sources.list"),
                content=io.BytesIO(lines.encode()),
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
    if original_mode == EmitterMode.NORMAL:
        emit.set_mode(EmitterMode.VERBOSE)
    with emit.open_stream(f"Running {full_run_cmd}") as stream:
        proc = instance.execute_run(
            full_run_cmd,
            cwd=remote_cwd,
            env=environment,
            stdout=stream,
            stderr=stream,
        )
    if original_mode == EmitterMode.NORMAL:
        emit.set_mode(original_mode)
    if proc.returncode != 0:
        raise CommandError(
            f"Job {job_name!r} for "
            f"{job.series}/{host_architecture} failed with "
            f"exit status {proc.returncode}.",
            retcode=proc.returncode,
        )


def _run_job(
    job_name: str,
    job: Job,
    provider: Provider,
    output: Optional[Path],
    apt_replacement_repositories: Optional[List[str]] = None,
    env_from_cli: Optional[List[str]] = None,
) -> None:
    """Run a single job."""
    # XXX jugmac00 2022-04-27: we should create a configuration object to be
    # passed in and not so many arguments
    host_architecture = get_host_architecture()
    if host_architecture not in job.architectures:
        return
    pm = get_plugin_manager(job)
    # XXX jugmac00 2021-12-17: extract inferring run_command
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
                apt_replacement_repositories=apt_replacement_repositories,
                environment=environment,
            )
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

        if job.output is not None and output is not None:
            target_path = output / job_name / job.series / host_architecture
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


def run(args: Namespace) -> int:
    """Run a pipeline, launching managed environments as needed."""
    # XXX jugmac00 2022-02-04: this fallback may become obsolete once we
    # use craft-cli's command dispatcher
    config_path = getattr(args, "config", Path(".launchpad.yaml"))
    config = Config.load(config_path)

    provider = get_provider()
    provider.ensure_provider_is_available()
    launched_instances = []

    try:
        for stage in config.pipeline:
            stage_failed = False
            for job_name in stage:
                try:
                    jobs = config.jobs.get(job_name, [])
                    if not jobs:
                        raise CommandError(
                            f"No job definition for {job_name!r}"
                        )
                    for job in jobs:
                        launched_instances.append(
                            _get_job_instance_name(provider, job)
                        )
                        _run_job(
                            job_name,
                            job,
                            provider,
                            getattr(args, "output_directory", None),
                            apt_replacement_repositories=getattr(
                                args, "apt_replace_repositories", None
                            ),
                            env_from_cli=getattr(args, "set_env", None),
                        )
                except CommandError as e:
                    if len(stage) == 1:
                        # Single-job stage, so just reraise this
                        # in order to get simpler error messages.
                        raise
                    else:
                        emit.error(e)
                        stage_failed = True
            if stage_failed:
                # FIXME: should we still clean here?
                raise CommandError(
                    f"Some jobs in {stage} failed; stopping.", retcode=1
                )
    finally:
        should_clean_environment = getattr(args, "clean", False)

        if should_clean_environment:
            cwd = Path.cwd()
            provider.clean_project_environments(
                project_name=cwd.name,
                project_path=cwd,
                instances=launched_instances,
            )
    return 0


def run_one(args: Namespace) -> int:
    """Select and run a single job from a pipeline.

    (This command is for use by Launchpad, and is subject to change.)
    """
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

    try:
        _run_job(
            args.job,
            job,
            provider,
            getattr(args, "output_directory", None),
            apt_replacement_repositories=getattr(
                args, "apt_replace_repositories", None
            ),
            env_from_cli=getattr(args, "set_env", None),
        )
    finally:
        should_clean_environment = getattr(args, "clean", False)

        if should_clean_environment:
            cwd = Path.cwd()
            provider.clean_project_environments(
                project_name=cwd.name,
                project_path=cwd,
                instances=[_get_job_instance_name(provider, job)],
            )

    return 0
