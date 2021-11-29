# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

import fnmatch
import io
import json
import os
from argparse import Namespace
from pathlib import Path, PurePath
from typing import List, Set

from craft_cli import emit
from craft_providers import Executor
from dotenv import dotenv_values

from lpcraft import env
from lpcraft.config import Config, Output
from lpcraft.errors import CommandError
from lpcraft.providers import get_provider
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
        properties.update(
            {
                key: value
                for key, value in dynamic_properties.items()
                if value is not None
            }
        )

    with open(target_path / "properties", "w") as f:
        json.dump(properties, f)


def run(args: Namespace) -> int:
    """Run a pipeline, launching managed environments as needed."""
    config = Config.load(Path(".launchpad.yaml"))
    host_architecture = get_host_architecture()
    cwd = Path.cwd()

    provider = get_provider()
    provider.ensure_provider_is_available()

    for job_name in config.pipeline:
        jobs = config.jobs.get(job_name, [])
        if not jobs:
            raise CommandError(f"No job definition for {job_name!r}")
        for job in jobs:
            if host_architecture not in job.architectures:
                continue
            if job.run is None:
                raise CommandError(
                    f"Job {job_name!r} for {job.series}/{host_architecture} "
                    f"does not set 'run'"
                )

            cmd = ["bash", "--noprofile", "--norc", "-ec", job.run]
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
                emit.progress("Running the job")
                with emit.open_stream(f"Running {cmd}") as stream:
                    proc = instance.execute_run(
                        cmd,
                        cwd=remote_cwd,
                        env=job.environment,
                        stdout=stream,
                        stderr=stream,
                    )
                if proc.returncode != 0:
                    raise CommandError(
                        f"Job {job_name!r} for "
                        f"{job.series}/{host_architecture} failed with "
                        f"exit status {proc.returncode}.",
                        retcode=proc.returncode,
                    )

                if job.output is not None and args.output is not None:
                    target_path = (
                        args.output / job_name / job.series / host_architecture
                    )
                    target_path.mkdir(parents=True, exist_ok=True)
                    _copy_output_paths(
                        job.output, remote_cwd, instance, target_path
                    )
                    _copy_output_properties(
                        job.output, remote_cwd, instance, target_path
                    )

    return 0
