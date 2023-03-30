# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

from __future__ import annotations  # isort:skip

__all__ = [
    "ToxPlugin",
    "PyProjectBuildPlugin",
    "MiniCondaPlugin",
    "CondaBuildPlugin",
    "GolangPlugin",
]

import textwrap
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, Dict, List, Optional, cast

import pydantic
from pydantic import StrictStr

from lpci.plugin import hookimpl
from lpci.plugins import register

# XXX: techalchemy 2022-03-25: prevent circular import of Job class
if TYPE_CHECKING:

    from lpci.config import Job  # pragma: no cover


class BaseConfig(
    pydantic.BaseModel,
    extra=pydantic.Extra.forbid,
    allow_mutation=False,
    alias_generator=lambda s: s.replace("_", "-"),
    underscore_attrs_are_private=True,
):
    """Base config for plugin models."""


class BasePlugin:

    INTERPOLATES_RUN_COMMAND: bool = False

    class Config(BaseConfig):
        pass

    def __init__(
        self, config: Job, plugin_settings: Optional[Dict[str, str]] = None
    ) -> None:
        self.config = config
        self.additional_settings = plugin_settings

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
    def lpci_install_packages(self) -> list[str]:
        return ["python3-pip"]

    @hookimpl  # type: ignore
    def lpci_execute_run(self) -> str:
        # XXX jugmac00 2022-01-07: we should consider using a requirements.txt
        # as this allows updating via `pip-tools`
        return "python3 -m pip install tox==3.24.5; tox"

    @hookimpl  # type: ignore
    def lpci_set_environment(self) -> dict[str, str | None]:
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
    def lpci_install_packages(self) -> list[str]:
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
    def lpci_execute_run(self) -> str:
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
        if self.additional_settings:
            soss_channel = self.additional_settings.get(
                "miniconda_conda_channel"
            )
            if soss_channel is not None:
                conda_channels.append(soss_channel)
        return conda_channels

    @hookimpl  # type: ignore
    def lpci_set_environment(self) -> dict[str, str]:
        # `CONDA_ENV` sets the name of the Conda virtual environment
        return {"CONDA_ENV": "lpci"}

    @hookimpl  # type: ignore
    def lpci_install_packages(self) -> list[str]:
        return [
            "git",
            "python3-dev",
            "python3-pip",
            "python3-venv",
            "wget",
        ]

    @hookimpl  # type: ignore
    def lpci_execute_before_run(self) -> str:
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
    def lpci_execute_run(self) -> str:
        run = self.config.run or ""
        return textwrap.dedent(
            f"""
        export PATH=$HOME/miniconda3/bin:$PATH
        source activate $CONDA_ENV
        {run}"""
        )

    @hookimpl  # type: ignore
    def lpci_execute_after_run(self) -> str:
        run = f"; {self.config.run_after}" if self.config.run_after else ""
        return (
            "export PATH=$HOME/miniconda3/bin:$PATH; "
            f"source activate $CONDA_ENV; conda env export{run}"
        )


@register(name="conda-build")
class CondaBuildPlugin(MiniCondaPlugin):
    """Sets up `miniconda3` and performs a `conda-build` on a package.

    Usage:
        In `.launchpad.yaml`, create the following structure:

        .. code-block:: yaml

           jobs:
               myjob:
                  plugin: conda-build
                  build-target: info/recipe/parent
                  conda-channels:
                    - conda-forge
                    - defaults
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

    class Config(MiniCondaPlugin.Config):
        build_target: Optional[StrictStr]
        conda_channels: Optional[List[StrictStr]]
        conda_packages: Optional[List[StrictStr]]
        conda_python: Optional[StrictStr]
        recipe_folder: Optional[StrictStr]

    DEFAULT_CONDA_PACKAGES = ("conda-build",)
    DEFAULT_RECIPE_FOLDER = "./info"

    def get_plugin_config(self) -> "CondaBuildPlugin.Config":
        return cast(CondaBuildPlugin.Config, self.config.plugin_config)

    @property
    def recipe_folder(self) -> str:
        recipe_folder = self.DEFAULT_RECIPE_FOLDER
        plugin_config = self.get_plugin_config()
        if plugin_config.recipe_folder:
            recipe_folder = plugin_config.recipe_folder
        return recipe_folder

    @staticmethod
    def _has_recipe(dir_: Path) -> bool:
        return dir_.joinpath("meta.yaml").is_file()

    @staticmethod
    def _rename_recipe_template(dir_: Path) -> None:
        # XXX techalchemy 2022-04-01: conda packages which are already built
        # and subsequently downloaded from the anaconda repositories retain
        # the templated recipe, at `meta.yaml.template`, but place the
        # rendered template at `meta.yaml`. The rendered recipes contain
        # hardcoded paths for a specific build environment and, for our
        # purposes, are not reusable. We need to render new ones from the
        # original templates.
        template_path = dir_.joinpath("meta.yaml.template")
        if template_path.is_file():
            template_path.replace(dir_ / "meta.yaml")

    def find_recipe(self) -> Path:
        def _find_recipe_dir(path: Path) -> Path:
            for subpath in path.iterdir():
                if subpath.is_dir():
                    self._rename_recipe_template(subpath)
                    if subpath.name == "recipe" and self._has_recipe(subpath):
                        return subpath
                    try:
                        return _find_recipe_dir(subpath)
                    except FileNotFoundError:
                        continue
            raise FileNotFoundError

        return _find_recipe_dir(Path(self.recipe_folder))

    def find_build_target(self) -> str:
        def find_parents(pth: Path) -> Path:
            for parent in pth.iterdir():
                if parent.is_dir():
                    self._rename_recipe_template(parent)
                    if parent.name == "parent" and self._has_recipe(parent):
                        return parent
            raise FileNotFoundError(pth.joinpath("meta.yaml"))

        try:
            recipe = self.find_recipe()
        except FileNotFoundError:
            raise RuntimeError("No build target found")
        try:
            # XXX techalchemy 2022-04-01: Some conda packages are built as
            # part of a parent package build process (e.g. `mkl-include` which
            # is built by `intel_repack`). If you acquire the child package
            # and attempt to build it (`mkl-include` in this case) it will
            # fail; you must build the parent instead if it exists
            return find_parents(recipe).as_posix()
        except FileNotFoundError:
            return recipe.as_posix()

    @property
    def build_configs(self) -> list[str]:
        try:
            recipe = self.find_recipe()
        except FileNotFoundError:
            return []
        configs = sorted(
            recipe.glob("**/conda_build_config.yaml"), reverse=True
        )
        return [_.as_posix() for _ in configs]

    @property
    def build_target(self) -> str:
        build_target = self.get_plugin_config().build_target
        if not build_target:
            return self.find_build_target()
        return build_target

    @hookimpl  # type: ignore
    def lpci_set_environment(self) -> dict[str, str]:
        # XXX techalchemy 2022-04-01: mypy is struggling with the super() call
        rv: dict[str, str] = super().lpci_set_environment()
        return rv

    @hookimpl  # type: ignore
    def lpci_execute_before_run(self) -> str:
        # XXX techalchemy 2022-04-01: mypy is struggling with the super() call
        rv: str = super().lpci_execute_before_run()
        return rv

    @hookimpl  # type: ignore
    def lpci_execute_after_run(self) -> str:
        # XXX techalchemy 2022-04-01: mypy is struggling with the super() call
        rv: str = super().lpci_execute_after_run()
        return rv

    @hookimpl  # type: ignore
    def lpci_install_packages(self) -> list[str]:
        # XXX techalchemy 2022-04-01: mypy is struggling with the super() call
        base_packages: list[str] = super().lpci_install_packages()
        base_packages.extend(
            [
                "automake",
                "build-essential",
                "cmake",
                "gcc",
                "g++",
                "libc++-dev",
                "libc6-dev",
                "libffi-dev",
                "libjpeg-dev",
                "libpng-dev",
                "libreadline-dev",
                "libsqlite3-dev",
                "libtool",
                "zlib1g-dev",
            ]
        )
        return base_packages

    @hookimpl  # type: ignore
    def lpci_execute_run(self) -> str:
        conda_channels = " ".join(f"-c {_}" for _ in self.conda_channels)
        conda_channels = f" {conda_channels}" if conda_channels else ""
        configs = " ".join(f"-m {_}" for _ in self.build_configs)
        configs = f" {configs}" if configs else ""
        build_command = "conda-build --no-anaconda-upload --output-folder dist"
        run_command = self.config.run or ""
        return textwrap.dedent(
            f"""
            export PATH=$HOME/miniconda3/bin:$PATH
            source activate $CONDA_ENV
            {build_command}{conda_channels}{configs} {self.build_target}
            {run_command}"""
        )


@register(name="golang")
class GolangPlugin(BasePlugin):
    """Installs the required `golang` version.

    Usage:
        In `.launchpad.yaml`, create the following structure. Please note that
        the `golang-version` has to be a string.

        .. code-block:: yaml

            pipeline:
                - build

            jobs:
                build:
                    plugin: golang
                    golang-version: "1.17"
                    series: focal
                    architectures: amd64
                    packages: [file, git]
                    run: go build -x examples/go-top.go

    Please note that the requested golang package needs to be available
    either in the standard repository or in a repository specified in
    `package-repositories`.
    """

    class Config(BaseConfig):
        golang_version: StrictStr

    INTERPOLATES_RUN_COMMAND = True

    def get_plugin_config(self) -> "GolangPlugin.Config":
        return cast(GolangPlugin.Config, self.config.plugin_config)

    @hookimpl  # type: ignore
    def lpci_install_packages(self) -> list[str]:
        version = self.get_plugin_config().golang_version
        return [f"golang-{version}"]

    @hookimpl  # type: ignore
    def lpci_execute_run(self) -> str:
        version = self.get_plugin_config().golang_version
        run_command = self.config.run or ""
        return textwrap.dedent(
            f"""
            export PATH=/usr/lib/go-{version}/bin/:$PATH
            {run_command}"""
        )
