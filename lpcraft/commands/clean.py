# Copyright 2022 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

from argparse import Namespace
from pathlib import Path

from craft_cli import emit

from lpcraft.config import Config
from lpcraft.providers import get_provider


def clean(args: Namespace) -> int:
    """Clean the managed environments for a project."""
    # We want to run the "clean" command only when run from
    # an lpcraft project directory.
    config_path = getattr(args, "config", Path(".launchpad.yaml"))
    Config.load(config_path)

    cwd = Path.cwd()
    emit.progress(
        f"Deleting the managed environments for the {cwd.name!r} project."
    )

    provider = get_provider()
    provider.ensure_provider_is_available()

    provider.clean_project_environments(
        project_name=cwd.name, project_path=cwd
    )
    emit.message(
        f"Deleted the managed environments for the {cwd.name!r} project."
    )
    return 0
