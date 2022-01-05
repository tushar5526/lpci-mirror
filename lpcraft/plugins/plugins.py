# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

from __future__ import annotations

__all__ = ["ToxPlugin"]

from lpcraft.config import Job
from lpcraft.plugin import hookimpl
from lpcraft.plugins import register


@register(name="tox")
class ToxPlugin:
    """Installs `tox` and executes the configured environments.

    Usage:
        In `.launchpad.yaml` create a key/value pair with `plugin` and `tox`
        within the job definition.
    """

    def __init__(self, config: Job) -> None:
        self.config = config

    @hookimpl  # type: ignore
    def lpcraft_install_packages(self) -> list[str]:
        return ["python3-pip"]

    @hookimpl  # type: ignore
    def lpcraft_execute_run(self) -> str:
        return "python3 -m pip install tox==3.24.5; tox"

    @hookimpl  # type: ignore
    def lpcraft_set_environment(self) -> dict[str, str | None]:
        # XXX jugmac00 2021-12-17: this was added to raise coverage and is not
        # necessary. Let's remove this once we have a plugin which actually
        # needs to set environment variables.
        return {"PLUGIN": "tox"}
