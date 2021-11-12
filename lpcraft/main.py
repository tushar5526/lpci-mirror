# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

"""Main entry point."""

import logging
import sys
from argparse import ArgumentParser

from craft_cli import CraftError, EmitterMode, emit

from lpcraft._version import version_description as lpcraft_version
from lpcraft.commands.version import version


def _configure_logger(name: str) -> None:
    """Configure a logger for use with craft-cli.

    Setting up a library's logger in DEBUG level causes its content to be
    grabbed by craft-cli's Emitter.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)


_configure_logger("craft_providers")


def main() -> int:
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

    subparsers = parser.add_subparsers()

    parser_version = subparsers.add_parser("version", help=version.__doc__)
    parser_version.set_defaults(func=version)

    emit.init(EmitterMode.NORMAL, "lpcraft", f"Starting {lpcraft_version}")

    try:
        args = parser.parse_args()
    except SystemExit:
        emit.ended_ok()
        return 1

    if args.quiet:
        emit.set_mode(EmitterMode.QUIET)
    elif args.verbose:
        emit.set_mode(EmitterMode.VERBOSE)

    if args.version:
        emit.message(lpcraft_version)
        emit.ended_ok()
        return 0

    if getattr(args, "func", None) is None:
        parser.print_usage(file=sys.stderr)
        emit.ended_ok()
        return 1

    try:
        ret = int(args.func(args))
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
