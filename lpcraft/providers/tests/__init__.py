# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

from dataclasses import dataclass

from craft_providers.lxd import LXDError, LXDInstallationError
from fixtures import MockPatch
from testtools import TestCase


class ProviderBaseTestCase(TestCase):
    def setUp(self):
        super().setUp()
        # Patch out inherited setup steps.
        self.useFixture(
            MockPatch(
                "craft_providers.bases.BuilddBase.setup",
                lambda *args, **kwargs: None,
            )
        )


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
