# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

"""Main entry point."""

import logging
from argparse import ArgumentParser
from pathlib import Path
from typing import List, Optional

from craft_cli import CraftError, EmitterMode, emit

from lpcraft._version import version_description as lpcraft_version
from lpcraft.commands.clean import clean
from lpcraft.commands.run import run, run_one
from lpcraft.commands.version import version
from lpcraft.errors import CommandError


def _configure_logger(name: str) -> None:
    """Configure a logger for use with craft-cli.

    Setting up a library's logger in DEBUG level causes its content to be
    grabbed by craft-cli's Emitter.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)


_configure_logger("craft_providers")


def main(argv: Optional[List[str]] = None) -> int:
    """lpcraft runs Launchpad CI jobs."""
    parser = ArgumentParser(description="Run Launchpad CI jobs.")
    parser.add_argument(
        "--version",
        action="store_true",
        help="Show version information and exit.",
    )

    verbosity_group = parser.add_mutually_exclusive_group()
    verbosity_group.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Only show warnings and errors, not progress.",
    )
    verbosity_group.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show debug information and be more verbose.",
    )
    verbosity_group.add_argument(
        "--trace",
        action="store_true",
        help="Show all information needed to trace internal behaviour.",
    )

    subparsers = parser.add_subparsers()

    # XXX cjwatson 2021-11-15: Subcommand arguments should be defined
    # alongside the individual subcommands rather than here.
    parser_clean = subparsers.add_parser(
        "clean", description=clean.__doc__, help=clean.__doc__
    )
    parser_clean.add_argument(
        "-c",
        "--config",
        type=Path,
        default=".launchpad.yaml",
        help="Read the configuration file from this path.",
    )
    parser_clean.set_defaults(func=clean)

    parser_run = subparsers.add_parser(
        "run", description=run.__doc__, help=run.__doc__
    )
    parser_run.add_argument(
        "--output-directory",
        type=Path,
        help="Write output files to this directory.",
    )
    parser_run.add_argument(
        "-c",
        "--config",
        type=Path,
        default=".launchpad.yaml",
        help="Read the configuration file from this path.",
    )
    parser_run.add_argument(
        "--clean",
        action="store_true",
        help=(
            "Clean the managed environments created "
            "for the pipeline after the running it."
        ),
    )
    parser_run.set_defaults(func=run)

    parser_run_one = subparsers.add_parser(
        "run-one", description=run_one.__doc__, help=run_one.__doc__
    )
    parser_run_one.add_argument(
        "--output-directory",
        type=Path,
        help="Write output files to this directory.",
    )
    parser_run_one.add_argument(
        "-c",
        "--config",
        type=Path,
        default=".launchpad.yaml",
        help="Read the configuration file from this path.",
    )
    parser_run_one.add_argument(
        "--clean",
        action="store_true",
        help=(
            "Clean the managed environment created for the job "
            "after running it."
        ),
    )
    parser_run_one.add_argument("job", help="Run only this job name.")
    parser_run_one.add_argument(
        "index",
        type=int,
        metavar="N",
        help="Run only the Nth job with the given name (indexing from 0).",
    )
    parser_run_one.set_defaults(func=run_one)

    parser_version = subparsers.add_parser(
        "version", description=version.__doc__, help=version.__doc__
    )
    parser_version.set_defaults(func=version)

    emit.init(EmitterMode.NORMAL, "lpcraft", f"Starting {lpcraft_version}")

    try:
        args = parser.parse_args(argv)
    except SystemExit:
        emit.ended_ok()
        return 1

    if args.quiet:
        emit.set_mode(EmitterMode.QUIET)
    elif args.verbose:
        emit.set_mode(EmitterMode.VERBOSE)
    elif args.trace:
        emit.set_mode(EmitterMode.TRACE)

    if args.version:
        emit.message(lpcraft_version)
        emit.ended_ok()
        return 0

    try:
        ret = int(getattr(args, "func", run)(args))
    except CommandError as e:
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
