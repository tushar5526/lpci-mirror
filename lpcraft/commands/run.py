# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

import subprocess
from argparse import Namespace
from pathlib import Path

from craft_cli import EmitterMode, emit

from lpcraft import env
from lpcraft.config import Config, Job, load
from lpcraft.errors import CommandError
from lpcraft.providers import get_provider, replay_logs
from lpcraft.utils import get_host_architecture


def _get_job(config: Config, job_name: str) -> Job:
    try:
        return config.jobs[job_name]
    except KeyError:
        raise CommandError(f"No job definition for {job_name!r}")


def _run_job(args: Namespace) -> None:
    """Run a single job in a managed environment."""
    if args.series is None:
        raise CommandError("Series is required in managed mode")
    if args.job_name is None:
        raise CommandError("Job name is required in managed mode")

    config = load(".launchpad.yaml")
    job = _get_job(config, args.job_name)
    if job.run is None:
        raise CommandError(f"'run' not set for job {args.job_name!r}")
    proc = subprocess.run(["bash", "--noprofile", "--norc", "-ec", job.run])
    if proc.returncode != 0:
        raise CommandError(
            f"Job {args.job_name!r} failed with exit status "
            f"{proc.returncode}.",
            retcode=proc.returncode,
        )


def _run_pipeline(args: Namespace) -> None:
    """Run a pipeline, launching managed environments as needed."""
    config = load(".launchpad.yaml")
    host_architecture = get_host_architecture()
    cwd = Path.cwd()

    provider = get_provider()
    provider.ensure_provider_is_available()

    for job_name in config.pipeline:
        job = _get_job(config, job_name)
        if host_architecture not in job.architectures:
            raise CommandError(
                f"Job {job_name!r} not defined for {host_architecture}"
            )

        cmd = ["lpcraft"]
        if emit.get_mode() == EmitterMode.QUIET:
            cmd.append("--quiet")
        elif emit.get_mode() == EmitterMode.VERBOSE:
            cmd.append("--verbose")
        elif emit.get_mode() == EmitterMode.TRACE:
            cmd.append("--trace")
        cmd.extend(["run", "--series", job.series, job_name])

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
                    cwd=env.get_managed_environment_project_path(),
                    stdout=stream,
                    stderr=stream,
                )
            if proc.returncode != 0:
                replay_logs(instance)
                raise CommandError(
                    f"Job {job_name!r} for {job.series}/{host_architecture} "
                    f"failed with exit status {proc.returncode}.",
                    retcode=proc.returncode,
                )


def run(args: Namespace) -> int:
    """Run a job."""
    if env.is_managed_mode():
        # XXX cjwatson 2021-11-09: Perhaps it would be simpler to split this
        # into a separate internal command instead?
        _run_job(args)
    else:
        _run_pipeline(args)
    return 0
