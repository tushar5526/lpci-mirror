# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

from __future__ import annotations  # isort:skip

__all__ = ["ToxPlugin", "PyProjectBuildPlugin", "MiniCondaPlugin"]

import textwrap
from typing import TYPE_CHECKING, ClassVar, List, Optional, cast

import pydantic
from pydantic import StrictStr

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

    INTERPOLATES_RUN_COMMAND: bool = False

    class Config(BaseConfig):
        pass

    def __init__(self, config: Job) -> None:
        self.config = config

    def get_plugin_config(self) -> BaseConfig:
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


@register(name="miniconda")
class MiniCondaPlugin(BasePlugin):
    """Installs `miniconda3` and resets the environment.

    Usage:
        In `.launchpad.yaml`, create the following structure:

        .. code-block:: yaml

           jobs:
               myjob:
                  plugin: miniconda
                  conda-packages:
                    - mamba
                    - numpy=1.17
                    - scipy
                    - pip
                  conda-python: 3.8
                  run: |
                    conda install ....
                    pip install --upgrade pytest
                    python -m build .
    """

    class Config(BaseConfig):
        conda_packages: Optional[List[StrictStr]]
        conda_python: Optional[StrictStr]
        conda_channels: Optional[List[StrictStr]]

        @pydantic.validator("conda_python", pre=True)
        def validate_conda_python(cls, v: str | float | int) -> str:
            return str(v)

    INTERPOLATES_RUN_COMMAND = True
    DEFAULT_CONDA_PACKAGES: ClassVar[tuple[str, ...]] = ("pip",)
    DEFAULT_CONDA_PYTHON = "3.8"
    DEFAULT_CONDA_CHANNELS = ("defaults",)

    def get_plugin_config(self) -> "MiniCondaPlugin.Config":
        return cast(MiniCondaPlugin.Config, self.config.plugin_config)

    @property
    def conda_packages(self) -> list[str]:
        conda_packages: set[str] = set()
        conda_python = self.DEFAULT_CONDA_PYTHON
        plugin_config = self.get_plugin_config()
        if plugin_config.conda_python:
            conda_python = plugin_config.conda_python
        if plugin_config.conda_packages:
            conda_packages.update(set(plugin_config.conda_packages))
        conda_packages.add(f"PYTHON={conda_python}")
        conda_packages.update(self.DEFAULT_CONDA_PACKAGES)
        return sorted(conda_packages)

    @property
    def conda_channels(self) -> list[str]:
        conda_channels: list[str] = []
        plugin_config = self.get_plugin_config()
        if plugin_config.conda_channels:
            conda_channels.extend(plugin_config.conda_channels)
        for channel in set(self.DEFAULT_CONDA_CHANNELS) - set(conda_channels):
            conda_channels.append(channel)
        return conda_channels

    @hookimpl  # type: ignore
    def lpcraft_set_environment(self) -> dict[str, str]:
        # `CONDA_ENV` sets the name of the Conda virtual environment
        return {"CONDA_ENV": "lpci"}

    @hookimpl  # type: ignore
    def lpcraft_install_packages(self) -> list[str]:
        return [
            "git",
            "python3-dev",
            "python3-pip",
            "python3-venv",
            "wget",
        ]

    @hookimpl  # type: ignore
    def lpcraft_execute_before_run(self) -> str:
        run = self.config.run_before or ""
        conda_channels = " ".join(f"-c {_}" for _ in self.conda_channels)
        return textwrap.dedent(
            f"""
        if [ ! -d "$HOME/miniconda3" ]; then
            wget -O /tmp/miniconda.sh https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh
            chmod +x /tmp/miniconda.sh
            /tmp/miniconda.sh -b
        fi
        export PATH=$HOME/miniconda3/bin:$PATH
        conda remove --all -q -y -n $CONDA_ENV
        conda create -n $CONDA_ENV -q -y {conda_channels} {' '.join(self.conda_packages)}
        source activate $CONDA_ENV
        {run}"""  # noqa:E501
        )

    @hookimpl  # type: ignore
    def lpcraft_execute_run(self) -> str:
        run = self.config.run or ""
        return textwrap.dedent(
            f"""
        export PATH=$HOME/miniconda3/bin:$PATH
        source activate $CONDA_ENV
        {run}"""
        )

    @hookimpl  # type: ignore
    def lpcraft_execute_after_run(self) -> str:
        run = f"; {self.config.run_after}" if self.config.run_after else ""
        return (
            "export PATH=$HOME/miniconda3/bin:$PATH; "
            f"source activate $CONDA_ENV; conda env export{run}"
        )
