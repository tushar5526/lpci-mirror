# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

from __future__ import annotations

__all__ = [
    "lpcraft_install_packages",
    "lpcraft_install_snaps",
    "lpcraft_execute_run",
    "lpcraft_set_environment",
]

import pluggy

from lpcraft.plugin import NAME

hookspec = pluggy.HookspecMarker(NAME)


@hookspec  # type: ignore
def lpcraft_install_packages() -> list[str]:
    """System packages to be installed."""


@hookspec  # type: ignore
def lpcraft_install_snaps() -> list[str]:
    """Snaps to be installed."""


@hookspec  # type: ignore
def lpcraft_execute_run() -> str:
    """Command to be executed."""
    # Please note: when both a plugin and the configuration file are
    # providing a `run` command, the one from the configuration file will be
    # used


@hookspec  # type: ignore
def lpcraft_set_environment() -> dict[str, str | None]:
    """Environment variables to be set."""
    # Please note: when there is the same environment variable provided by
    # the plugin and the configuration file, the one in the configuration
    # file will be taken into account
