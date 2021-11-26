# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

from argparse import Namespace
from pathlib import Path

from craft_cli import emit

from lpcraft import env
from lpcraft.config import Config
from lpcraft.errors import CommandError
from lpcraft.providers import get_provider
from lpcraft.utils import get_host_architecture


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

    return 0
