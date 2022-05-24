# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

from __future__ import annotations  # isort:skip

__all__ = ["ToxPlugin", "PyProjectBuildPlugin"]

from typing import TYPE_CHECKING

import pydantic

from lpcraft.plugin import hookimpl
from lpcraft.plugins import register

# XXX: techalchemy 2022-03-25: prevent circular import of Job class
if TYPE_CHECKING:

    from lpcraft.config import Job  # pragma: no cover


class BaseConfig(
    pydantic.BaseModel,
    extra=pydantic.Extra.forbid,
    frozen=True,
    alias_generator=lambda s: s.replace("_", "-"),
    underscore_attrs_are_private=True,
):
    """Base config for plugin models."""


class BasePlugin:
    class Config(BaseConfig):
        pass

    def __init__(self, config: Job) -> None:
        self.config = config

    def get_plugin_config(self):
        """Return the properly typecast plugin configuration."""
        raise NotImplementedError


@register(name="tox")
class ToxPlugin(BasePlugin):
    """Installs `tox` and executes the configured environments.

    Usage:
        In `.launchpad.yaml` create a key/value pair with `plugin` and `tox`
        within the job definition.
    """

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
        # Work around https://github.com/tox-dev/tox/issues/2372: without
        # this, tox won't pass through the lower-case proxy environment
        # variables set by launchpad-buildd.
        return {"TOX_TESTENV_PASSENV": "http_proxy https_proxy"}


@register(name="pyproject-build")
class PyProjectBuildPlugin(BasePlugin):
    """Installs `build` and builds a Python package according to PEP 517.

    Usage:
        In `.launchpad.yaml` create a key/value pair with `plugin` and
        `pyproject-build` within the job definition.
    """

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
