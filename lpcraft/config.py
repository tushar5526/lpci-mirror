# Copyright 2021-2022 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

import re
from datetime import timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple, Type, Union

import pydantic
from craft_cli import emit
from pydantic import AnyHttpUrl, StrictStr, root_validator, validator

from lpcraft.errors import ConfigurationError
from lpcraft.plugins import PLUGINS
from lpcraft.plugins.plugins import BaseConfig, BasePlugin
from lpcraft.utils import load_yaml

LAUNCHPAD_PPA_BASE_URL = "https://ppa.launchpadcontent.net"


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

    paths: Optional[List[StrictStr]] = None
    distribute: Optional[OutputDistributeEnum] = None
    channels: Optional[List[StrictStr]] = None
    # instead of `Any` this should be something like `JSONSerializable`
    properties: Optional[Dict[StrictStr, Any]] = None
    dynamic_properties: Optional[Path] = None
    expires: Optional[timedelta] = None

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

    # XXX jugmac00 2023-03-10 the intention of this class was to verify that
    # only supported distroseries are present in the .launchpad.yaml file
    # but this does not work as intended, as you can specify arbitrary
    # strings which later possibly result in a KeyError
    bionic = "bionic"  # 18.04
    focal = "focal"  # 20.04
    jammy = "jammy"  # 22.04


class PPAShortFormURL(pydantic.ConstrainedStr):
    """A string with a constrained syntax to match a PPA short form URL."""

    strict = True
    # Support the two-segment form: OWNER/ARCHIVE (e.g. `launchpad/ppa`)
    # and the three-segment form: OWNER/DISTRIBUTION/ARCHIVE
    # (e.g. `launchpad/debian/ppa`).
    regex = re.compile(
        r"^[a-z0-9][a-z0-9\+\._\-]+(/[a-z0-9][a-z0-9\+\._\-]+){1,2}$"
    )


def get_ppa_url_parts(ppa_url: PPAShortFormURL) -> Tuple[str, str, str]:
    """Split and return the parts of a PPA short-form URL."""
    ppa_url_parts = ppa_url.split("/")
    if len(ppa_url_parts) == 2:
        owner, archive = ppa_url_parts
        distribution = "ubuntu"
    else:
        owner, distribution, archive = ppa_url_parts
    return owner, distribution, archive


class PackageRepository(ModelConfigDefaults):
    """A representation of a package repository.

    inspired by https://snapcraft.io/docs/package-repositories
    """

    type: PackageType  # e.g. `apt``
    ppa: Optional[PPAShortFormURL] = None  # e.g. `launchpad/ubuntu/ppa`
    formats: Optional[List[PackageFormat]] = None  # e.g. `[deb, deb-src]`
    components: Optional[List[PackageComponent]] = None  # e.g. `[main]`
    suites: Optional[List[PackageSuite]] = None  # e.g. `[bionic, focal]`
    url: Optional[AnyHttpUrl] = None
    trusted: Optional[bool] = False

    @root_validator(pre=True)
    def validate_multiple_fields(
        cls, values: Dict[str, Any]
    ) -> Dict[str, Any]:
        if "url" in values:
            if "ppa" in values:
                raise ValueError(
                    "Only one of the following keys can be specified:"
                    " 'url', 'ppa'."
                )
            if "components" not in values:
                raise ValueError(
                    "The 'components' key is required when the 'url' key"
                    " is specified."
                )
        else:
            if "ppa" not in values:
                raise ValueError(
                    "One of the following keys is required with an appropriate"
                    " value: 'url', 'ppa'."
                )
            if "components" in values:
                raise ValueError(
                    "The 'components' key is not allowed when the 'ppa' key is"
                    " specified. PPAs only support the 'main' component."
                )

        return values

    @validator("components", pre=True, always=True)
    def infer_components_if_ppa_is_set(
        cls, v: List[PackageComponent], values: Dict[str, Any]
    ) -> List[PackageComponent]:
        if v is None and values["ppa"]:
            return ["main"]
        return v

    @validator("url", pre=True, always=True)
    def infer_url_if_ppa_is_set(
        cls, v: AnyHttpUrl, values: Dict[str, Any]
    ) -> AnyHttpUrl:
        if v is None and values["ppa"]:
            owner, distribution, archive = get_ppa_url_parts(values["ppa"])
            v = "{}/{}/{}/{}".format(
                LAUNCHPAD_PPA_BASE_URL,
                owner,
                archive,
                distribution,
            )
        return v

    @validator("formats", pre=True, always=True)
    def set_formats_default_value(
        cls, v: List[PackageFormat]
    ) -> List[PackageFormat]:
        if not v:
            v = [PackageFormat.deb]
        return v

    @validator("trusted")
    def convert_trusted(cls, v: bool) -> str:
        # trusted is True or False, but we need `yes` or `no`
        return v and "yes" or "no"

    def sources_list_lines(self) -> Iterator[str]:
        """Yield repository lines as strings.

        e.g. 'deb https://canonical.example.org/artifactory/jammy-golang-backport focal main'
        """  # noqa: E501
        assert self.formats is not None
        assert self.suites is not None
        for format in self.formats:
            for suite in self.suites:
                assert self.components is not None
                if self.trusted:
                    yield f"{format.value} [trusted={self.trusted}] {self.url!s} {suite.value} {' '.join(self.components)}"  # noqa: E501
                else:
                    yield f"{format.value} {self.url!s} {suite.value} {' '.join(self.components)}"  # noqa: E501


class Snap(ModelConfigDefaults):
    """A snap definition."""

    name: StrictStr
    channel: Optional[StrictStr] = "latest/stable"
    classic: Optional[bool] = False

    @validator("channel")
    def prevent_channel_none(cls, v: StrictStr) -> Any:
        if v is None:
            raise ValueError(
                "You configured a Snap `channel`, "
                + "but you did not specify a value."
            )
        return v

    @validator("classic")
    def prevent_classic_none(cls, v: bool) -> Any:
        if v is None:
            raise ValueError(
                "You configured a Snap `classic`, "
                + "but you did not specify a value. "
                + "Valid values would either be `True` or `False`."
            )
        return v


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
    snaps: Optional[List[Snap]]
    packages: Optional[List[StrictStr]]
    package_repositories: List[PackageRepository] = []
    plugin: Optional[StrictStr]
    plugin_config: Optional[BaseConfig]

    @pydantic.validator("architectures", pre=True)
    def validate_architectures(
        cls, v: Union[_Identifier, List[_Identifier]]
    ) -> List[_Identifier]:
        if isinstance(v, str):
            v = [v]
        return v

    @pydantic.validator("snaps", pre=True)
    def validate_snaps(cls, v: List[Any]) -> Any:
        clean_values = []
        for value in v:
            # Backward compatibility, i.e. [chromium, firefox]
            if type(value) is str:
                emit.message(
                    f"Warning: You configured snap `{value}` but "
                    + "you used a deprecated format. "
                    + "\nPlease use "
                    + f"\n...\n-name: {value}\n"
                    + " classic: True\n...\n"
                    + "instead.\n"
                    + "Please refer to the documentation for an "
                    + "overview of supported formats.",
                )
                clean_values.append({"name": value, "classic": True})
            elif type(value) is dict:
                if "name" not in value or value["name"] is None:
                    raise ValueError(
                        "You configured a Snap "
                        + "but you did not specify a name."
                    )
                if "classic" in value and value["classic"] is not None:
                    if type(value["classic"]) is not bool:
                        raise ValueError(
                            "You configured a Snap `classic`, "
                            + "but you did not specify a valid value. "
                            + "Valid values would either be `True` or `False`."
                        )
                clean_values.append(value)
            else:
                raise ValueError(
                    "You configured a Snap, "
                    + "but you used an unknown format. "
                    + "Please refer to the documentation for an "
                    + "overview of supported formats."
                )
        return clean_values

    @pydantic.validator("package_repositories")
    def validate_package_repositories(
        cls, v: List[PackageRepository], values: Dict[StrictStr, Any]
    ) -> List[PackageRepository]:
        package_repositories = None
        for index, package_repository in enumerate(v):
            if not package_repository.suites:
                if not package_repositories:
                    package_repositories = v.copy()
                package_repositories[index].suites = [
                    PackageSuite[values["series"]]
                ]
        return package_repositories or v

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
