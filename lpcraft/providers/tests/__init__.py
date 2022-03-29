# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

from dataclasses import dataclass
from typing import Optional
from unittest.mock import Mock

from craft_providers.lxd import LXC, LXDError, LXDInstallationError, launch

from lpcraft.providers._lxd import LXDProvider, _LXDLauncher


@dataclass
class FakeLXDInstaller:
    """A fake LXD installer implementation for tests."""

    can_install: bool = True
    already_installed: bool = True
    is_ready: bool = True

    def install(self) -> str:
        raise LXDInstallationError("Cannot install LXD")

    def is_installed(self) -> bool:
        return self.already_installed

    def ensure_lxd_is_ready(self) -> None:
        if not self.is_ready:
            raise LXDError("LXD is broken")


def makeLXDProvider(
    lxc: Optional[LXC] = None,
    can_install: bool = True,
    already_installed: bool = True,
    is_ready: bool = True,
    lxd_launcher: Optional[_LXDLauncher] = None,
    lxd_project: str = "test-project",
    lxd_remote: str = "test-remote",
) -> LXDProvider:
    """Create a custom LXDProvider for tests."""
    if lxc is None:
        lxc = Mock(spec=LXC)
        lxc.remote_list.return_value = {}
    lxd_installer = FakeLXDInstaller(
        can_install=can_install,
        already_installed=already_installed,
        is_ready=is_ready,
    )
    if lxd_launcher is None:
        lxd_launcher = Mock(spec=launch)
    return LXDProvider(
        lxc=lxc,
        lxd_installer=lxd_installer,
        lxd_launcher=lxd_launcher,
        lxd_project=lxd_project,
        lxd_remote=lxd_remote,
    )
