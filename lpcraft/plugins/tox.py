# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

from __future__ import annotations

from lpcraft.config import Job
from lpcraft.plugin import hookimpl


class ToxPlugin:
    # XXX jugmac00 2021-12-16: this plugin is not yet fully implemented
    def __init__(self, config: Job) -> None:
        self.config = config

    @hookimpl  # type: ignore
    def lpcraft_install_packages(self) -> list[str]:
        return ["tox"]
