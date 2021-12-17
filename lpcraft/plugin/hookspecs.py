# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

from __future__ import annotations

import pluggy

hookspec = pluggy.HookspecMarker("lpcraft")


@hookspec  # type: ignore
def lpcraft_install_packages() -> list[str]:
    """system packages to be installed"""


@hookspec  # type: ignore
def lpcraft_install_snaps() -> list[str]:
    """snaps to be installed"""


@hookspec  # type: ignore
def lpcraft_execute_run() -> str:
    """command to be executed"""


@hookspec  # type: ignore
def lpcraft_set_environment() -> dict[str, str | None]:
    """environment variables to be set"""
    # Please note: when there is the same environment variable provided by
    # the plugin and the configuration file, the one in the configuration
    # file will be taken into account
