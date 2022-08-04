# Copyright 2021-2022 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

import re
from datetime import timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Type, Union

import pydantic
from pydantic import AnyHttpUrl, StrictStr, validator

from lpcraft.errors import ConfigurationError
from lpcraft.plugins import PLUGINS
from lpcraft.plugins.plugins import BaseConfig, BasePlugin
from lpcraft.utils import load_yaml


class _Identifier(pydantic.ConstrainedStr):
    """A string with constrained syntax used as a short identifier.

    Compare `lp.app.validators.name` in Launchpad, though we also permit
    underscores here.
    """

    strict = True
    regex = re.compile(r"^[a-z0-9][a-z0-9\+\._\-]+$")


class ModelConfigDefaults(
    pydantic.BaseModel,
    extra=pydantic.Extra.forbid,
    alias_generator=lambda s: s.replace("_", "-"),
    underscore_attrs_are_private=True,
):
    """Define lpcraft's model defaults."""


class OutputDistributeEnum(Enum):
    """Valid values for `output.distribute`."""

    artifactory = "artifactory"


class Output(ModelConfigDefaults):
    """Job output properties."""

    paths: Optional[List[StrictStr]]
    distribute: Optional[OutputDistributeEnum]
    channels: Optional[List[StrictStr]]
    # instead of `Any` this should be something like `JSONSerializable`
    properties: Optional[Dict[StrictStr, Any]]
    dynamic_properties: Optional[Path]
    expires: Optional[timedelta]

    @pydantic.validator("expires")
    def validate_expires(cls, v: timedelta) -> timedelta:
        if v < timedelta(0):
            raise ValueError("non-negative duration expected")
        return v


class Input(ModelConfigDefaults):
    """Job input properties."""

    job_name: StrictStr
    target_directory: StrictStr


def _validate_plugin_config(
    plugin: Type[BasePlugin],
    values: Dict[StrictStr, Any],
    job_fields: List[str],
) -> Dict[StrictStr, Any]:
    plugin_config = {}
    for k in plugin.Config.schema()["properties"].keys():
        # configuration key belongs to the plugin
        if k in values and k not in job_fields:
            # TODO: should some error be raised if a plugin tries consuming
            # a job configuration key?
            plugin_config[k] = values.pop(k)
    values["plugin-config"] = plugin.Config.parse_obj(plugin_config)
    return values


class PackageType(str, Enum):
    """Specifies the type of the package repository.

    Currently only supports apt.
    """

    apt = "apt"


class PackageFormat(str, Enum):
    """Specifies the format of the package repository."""

    deb = "deb"
    deb_src = "deb-src"


class PackageComponent(str, Enum):
    """Specifies the component of the package repository."""

    main = "main"
    restricted = "restricted"
    universe = "universe"
    multiverse = "multiverse"


class PackageSuite(str, Enum):
    """Specifies the suite of the package repository.

    e.g. xenial, focal, ...
    """

    bionic = "bionic"  # 18.04
    focal = "focal"  # 20.04
    jammy = "jammy"  # 22.04


class PackageRepository(ModelConfigDefaults):
    """A representation of a package repository.

    inspired by https://snapcraft.io/docs/package-repositories
    """

    type: PackageType  # e.g. `apt``
    formats: List[PackageFormat]  # e.g. `[deb, deb-src]`
    components: List[PackageComponent]  # e.g. `[main, universe]`
    suites: List[PackageSuite]  # e.g. `[bionic, focal]`
    url: AnyHttpUrl
    trusted: Optional[bool]

    @validator("trusted")
    def convert_trusted(cls, v: bool) -> str:
        # trusted is True or False, but we need `yes` or `no`
        return v and "yes" or "no"

    def sources_list_lines(self) -> Iterator[str]:
        """Yield repository lines as strings.

        e.g. 'deb https://canonical.example.org/artifactory/jammy-golang-backport focal main'
        """  # noqa: E501
        for format in self.formats:
            for suite in self.suites:
                if self.trusted:
                    yield f"{format} [trusted={self.trusted}] {self.url!s} {suite} {' '.join(self.components)}"  # noqa: E501
                else:
                    yield f"{format} {self.url!s} {suite} {' '.join(self.components)}"  # noqa: E501


class Job(ModelConfigDefaults):
    """A job definition."""

    # XXX jugmac00 2012-12-17: working with Job's attributes could be
    # simplified if they would not be optional, but rather return e.g.
    # an empty list

    series: _Identifier
    architectures: List[_Identifier]
    run_before: Optional[StrictStr]
    run: Optional[StrictStr]
    run_after: Optional[StrictStr]
    environment: Optional[Dict[str, Optional[str]]]
    output: Optional[Output]
    input: Optional[Input]
    snaps: Optional[List[StrictStr]]
    packages: Optional[List[StrictStr]]
    package_repositories: Optional[List[PackageRepository]]
    plugin: Optional[StrictStr]
    plugin_config: Optional[BaseConfig]

    @pydantic.validator("architectures", pre=True)
    def validate_architectures(
        cls, v: Union[_Identifier, List[_Identifier]]
    ) -> List[_Identifier]:
        if isinstance(v, str):
            v = [v]
        return v

    @pydantic.root_validator(pre=True)
    def move_plugin_config_settings(
        cls, values: Dict[StrictStr, Any]
    ) -> Dict[StrictStr, Any]:
        """Delegate plugin settings to the plugin."""
        if "plugin" in values:
            base_values = values.copy()
            if values["plugin"] not in PLUGINS:
                raise ConfigurationError("Unknown plugin")
            plugin = PLUGINS[values["plugin"]]
            return _validate_plugin_config(
                plugin=plugin,
                values=base_values,
                job_fields=list(cls.__fields__.keys()),
            )
        return values


def _expand_job_values(
    values: Dict[StrictStr, Any]
) -> List[Dict[StrictStr, Any]]:
    expanded_values = []
    if "matrix" in values:
        base_values = values.copy()
        del base_values["matrix"]
        for variant in values["matrix"]:
            variant_values = base_values.copy()
            variant_values.update(variant)
            expanded_values.append(variant_values)
    else:
        expanded_values.append(values)
    return expanded_values


class License(ModelConfigDefaults):
    """A representation of a license."""

    # We do not need to check that at least one value is set, as currently
    # there are only these two values, no others. That means not setting any of
    # them will not result in the creation of a `License` object.
    # Once we have more fields, we need to add e.g. a root validator, see
    # https://stackoverflow.com/questions/58958970

    # XXX jugmac00 2022-08-03: add validator for spdx identifier
    # XXX jugmac00 2022-08-04: add validator for path

    spdx: Optional[StrictStr] = None
    path: Optional[StrictStr] = None

    @validator("path", always=True)
    def disallow_setting_both_sources(
        cls, path: str, values: Dict[str, str]
    ) -> str:
        if values.get("spdx") and path:
            raise ValueError(
                "You cannot set `spdx` and `path` at the same time."
            )
        return path


class Config(ModelConfigDefaults):
    """A .launchpad.yaml configuration file."""

    pipeline: List[List[_Identifier]]
    jobs: Dict[StrictStr, List[Job]]
    license: Optional[License]

    @pydantic.validator("pipeline", pre=True)
    def validate_pipeline(
        cls, v: List[Union[_Identifier, List[_Identifier]]]
    ) -> List[List[_Identifier]]:
        return [[stage] if isinstance(stage, str) else stage for stage in v]

    # XXX cjwatson 2021-11-17: This expansion strategy works, but it may
    # produce suboptimal error messages, and doesn't have a good way to do
    # things like limiting the keys that can be set in a matrix.
    @pydantic.root_validator(pre=True)
    def expand_matrix(
        cls, values: Dict[StrictStr, Any]
    ) -> Dict[StrictStr, Any]:
        expanded_values = values.copy()
        expanded_values["jobs"] = {
            job_name: _expand_job_values(job_values)
            for job_name, job_values in values["jobs"].items()
        }
        return expanded_values

    @classmethod
    def load(cls, path: Path) -> "Config":
        """Load config from the indicated file name."""
        # XXX lgp171188 2022-03-31: it is not a good idea to evaluate
        # `Path.cwd()` in multiple places to determine the project directory.
        # This could be made available as an attribute on the `Config` class
        # instead.
        project_dir = Path.cwd()
        resolved_path = path.resolve()
        try:
            # XXX lgp171188 2022-04-04: There is a new method,
            # Path.is_relative_to() in Python 3.9+, which does
            # exactly what we need. Once we drop support
            # for Python 3.8, we should switch to that instead.
            resolved_path.relative_to(project_dir)
        except ValueError:
            raise ConfigurationError(
                f"'{resolved_path}' is not in the subpath of '{project_dir}'."
            )
        content = load_yaml(path)
        return cls.parse_obj(content)
