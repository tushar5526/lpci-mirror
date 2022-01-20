# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

from __future__ import annotations

__all__ = ["ToxPlugin", "PyProjectBuildPlugin"]

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
        # XXX jugmac00 2022-01-07: we should consider using a requirements.txt
        # as this allows updating via `pip-tools`
        return "python3 -m pip install tox==3.24.5; tox"

    @hookimpl  # type: ignore
    def lpcraft_set_environment(self) -> dict[str, str | None]:
        # XXX jugmac00 2021-12-17: this was added to raise coverage and is not
        # necessary. Let's remove this once we have a plugin which actually
        # needs to set environment variables.
        return {"PLUGIN": "tox"}


@register(name="pyproject-build")
class PyProjectBuildPlugin:
    """Installs `build` and builds a Python package according to PEP 517.

    Usage:
        In `.launchpad.yaml` create a key/value pair with `plugin` and
        `pyproject-build` within the job definition.
    """

    def __init__(self, config: Job) -> None:
        self.config = config

    @hookimpl  # type: ignore
    def lpcraft_install_packages(self) -> list[str]:
        # Ubuntu 20.04 does not provide a packaged version of build,
        # so we need pip to install it
        #
        # `build` needs `python3-venv` to create an isolated build
        # environment
        return [
            "python3-pip",
            "python3-venv",
        ]

    @hookimpl  # type: ignore
    def lpcraft_execute_run(self) -> str:
        # XXX jugmac00 2022-01-20: we should consider using a PPA
        return "python3 -m pip install build==0.7.0; python3 -m build"
