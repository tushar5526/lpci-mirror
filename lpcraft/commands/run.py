# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

import fnmatch
import io
import itertools
import json
import os
from argparse import Namespace
from pathlib import Path, PurePath
from typing import List, Optional, Set

from craft_cli import EmitterMode, emit
from craft_providers import Executor
from craft_providers.actions.snap_installer import install_from_store
from dotenv import dotenv_values

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
            remote_cwd,
        )

    remote_paths = sorted(_list_files(instance, remote_cwd))
    output_files = target_path / "files"

    filtered_paths: Set[PurePath] = set()
    for path_pattern in output.paths:
        filtered_paths.update(
            PurePath(name)
            for name in fnmatch.filter(
                [str(path) for path in remote_paths],
                path_pattern,
            )
        )
    resolved_paths = _resolve_symlinks(
        instance,
        [remote_cwd / path for path in sorted(filtered_paths)],
    )

    for path in sorted(resolved_paths):
        relative_path = _check_relative_path(path, remote_cwd)
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


def _run_job(
    job_name: str, job: Job, provider: Provider, output: Optional[Path]
) -> None:
    """Run a single job."""
    host_architecture = get_host_architecture()
    if host_architecture not in job.architectures:
        return
    pm = get_plugin_manager(job)
    # XXX jugmac00 2021-12-17: extract infering run_command
    run_command = None

    run_from_configuration = job.run
    if run_from_configuration is not None:
        run_command = run_from_configuration
    else:
        rv = pm.hook.lpcraft_execute_run()
        run_command = rv and rv[0] or None

    if not run_command:
        raise CommandError(
            f"Job {job_name!r} for {job.series}/{host_architecture} "
            f"does not set 'run'"
        )

    # XXX jugmac00 2021-12-17: extract infering environment variables
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
                channel="stable",
                classic=True,
            )
        packages = list(itertools.chain(*pm.hook.lpcraft_install_packages()))
        if packages:
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
        full_run_cmd = ["bash", "--noprofile", "--norc", "-ec", run_command]
        emit.progress("Running the job")
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

        if job.output is not None and output is not None:
            target_path = output / job_name / job.series / host_architecture
            target_path.mkdir(parents=True, exist_ok=True)
            _copy_output_paths(job.output, remote_cwd, instance, target_path)
            _copy_output_properties(
                job.output, remote_cwd, instance, target_path
            )


def run(args: Namespace) -> int:
    """Run a pipeline, launching managed environments as needed."""
    config = Config.load(Path(".launchpad.yaml"))

    provider = get_provider()
    provider.ensure_provider_is_available()

    for job_name in config.pipeline:
        jobs = config.jobs.get(job_name, [])
        if not jobs:
            raise CommandError(f"No job definition for {job_name!r}")
        for job in jobs:
            _run_job(job_name, job, provider, getattr(args, "output", None))

    return 0


def run_one(args: Namespace) -> int:
    """Select and run a single job from a pipeline.

    (This command is for use by Launchpad, and is subject to change.)
    """
    config = Config.load(Path(".launchpad.yaml"))

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

    _run_job(args.job, job, provider, getattr(args, "output", None))

    return 0
