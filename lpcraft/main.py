# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

"""Main entry point."""

import logging
import sys
from typing import List, Optional

from craft_cli import (
    ArgumentParsingError,
    CommandGroup,
    CraftError,
    Dispatcher,
    EmitterMode,
    GlobalArgument,
    ProvideHelpException,
    emit,
)

from lpcraft._version import version_description as lpcraft_version
from lpcraft.commands.clean import CleanCommand
from lpcraft.commands.run import RunCommand, RunOneCommand
from lpcraft.commands.version import VersionCommand


def _configure_logger(name: str) -> None:
    """Configure a logger for use with craft-cli.

    Setting up a library's logger in DEBUG level causes its content to be
    grabbed by craft-cli's Emitter.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)


_configure_logger("craft_providers")


_basic_commands = [
    CleanCommand,
    RunCommand,
    RunOneCommand,
    VersionCommand,
]


def main(argv: Optional[List[str]] = None) -> int:
    """`lpcraft` runs Launchpad CI jobs."""
    if argv is None:
        argv = sys.argv[1:]

    emit.init(EmitterMode.BRIEF, "lpcraft", f"Starting {lpcraft_version}")
    command_groups = [CommandGroup("Basic", _basic_commands)]
    summary = "Run Launchpad CI jobs."
    extra_global_args = [
        GlobalArgument(
            "version",
            "flag",
            "-V",
            "--version",
            "Show version information and exit",
        )
    ]

    # dispatcher = Dispatcher(
    #     "lpcraft",
    #     command_groups,
    #     summary=summary,
    #     extra_global_args=extra_global_args,
    #     default_command=RunCommand,
    # )
    # global_args = dispatcher.pre_parse_args(argv)
    # if global_args["version"]:
    #     emit.message(lpcraft_version)
    #     emit.ended_ok()
    #     return 0
    # dispatcher.load_command(None)
    # ret = dispatcher.run() or 0

    try:
        dispatcher = Dispatcher(
            "lpcraft",
            command_groups,
            summary=summary,
            extra_global_args=extra_global_args,
            default_command=RunCommand,
        )
        global_args = dispatcher.pre_parse_args(argv)
        if global_args["version"]:
            emit.message(lpcraft_version)
            emit.ended_ok()
            return 0
        dispatcher.load_command(None)
        ret = dispatcher.run() or 0
    except ArgumentParsingError as e:
        print(e, file=sys.stderr)
        emit.ended_ok()
        ret = 1
    except ProvideHelpException as e:
        print(e)
        emit.ended_ok()
        ret = 0
    except CraftError as e:
        emit.error(e)
        ret = e.retcode
    except KeyboardInterrupt as e:
        error = CraftError("Interrupted.")
        error.__cause__ = e
        emit.error(error)
        ret = 1
    except Exception as e:
        error = CraftError(f"lpcraft internal error: {e!r}")
        error.__cause__ = e
        emit.error(error)
        ret = 1
    else:
        emit.ended_ok()

    return ret
