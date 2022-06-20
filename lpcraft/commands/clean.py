# Copyright 2022 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

from argparse import ArgumentParser, Namespace
from pathlib import Path

from craft_cli import BaseCommand, emit

from lpcraft.config import Config
from lpcraft.providers import get_provider


class CleanCommand(BaseCommand):
    """Clean the managed environments for a project."""

    name = "clean"
    help_msg = __doc__.splitlines()[0]
    overview = __doc__
    common = True

    def fill_parser(self, parser: ArgumentParser) -> None:
        """Add arguments specific to this command."""
        parser.add_argument(
            "-c",
            "--config",
            type=Path,
            default=".launchpad.yaml",
            help="Read the configuration file from this path.",
        )

    def run(self, args: Namespace) -> int:
        """Run the command."""
        # We want to run the "clean" command only when run from an lpcraft
        # project directory, so we load the config here even though we don't
        # do anything with it.
        Config.load(args.config)

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
