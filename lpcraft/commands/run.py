# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

import subprocess
from argparse import Namespace
from pathlib import Path
from typing import List, Optional

from craft_cli import EmitterMode, emit

from lpcraft import env
from lpcraft.config import Config, Job
from lpcraft.errors import CommandError
from lpcraft.providers import get_provider, replay_logs
from lpcraft.utils import get_host_architecture


def _get_jobs(
    config: Config, job_name: str, series: Optional[str] = None
) -> List[Job]:
    jobs = config.jobs.get(job_name, [])
    if not jobs:
        raise CommandError(f"No job definition for {job_name!r}")
    if series is not None:
        jobs = [job for job in jobs if job.series == series]
        if not jobs:
            raise CommandError(
                f"No job definition for {job_name!r} for {series}"
            )
    return jobs


def _run_job(args: Namespace) -> None:
    """Run a single job in a managed environment."""
    if args.series is None:
        raise CommandError("Series is required in managed mode")
    if args.job_name is None:
        raise CommandError("Job name is required in managed mode")

    config = Config.load(Path(".launchpad.yaml"))
    jobs = _get_jobs(config, args.job_name, series=args.series)
    if len(jobs) > 1:
        raise CommandError(
            f"Ambiguous job definitions for {args.job_name!r} for "
            f"{args.series}"
        )
    [job] = jobs
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
    config = Config.load(Path(".launchpad.yaml"))
    host_architecture = get_host_architecture()
    cwd = Path.cwd()

    provider = get_provider()
    provider.ensure_provider_is_available()

    for job_name in config.pipeline:
        jobs = _get_jobs(config, job_name)
        for job in jobs:
            if host_architecture not in job.architectures:
                continue

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
                        f"Job {job_name!r} for "
                        f"{job.series}/{host_architecture} failed with "
                        f"exit status {proc.returncode}.",
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
