# Copyright 2021-2022 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

import re
from datetime import timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pydantic
from pydantic import StrictStr

from lpcraft.errors import ConfigurationError
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
    frozen=True,
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
    properties: Optional[Dict[StrictStr, StrictStr]]
    dynamic_properties: Optional[Path]
    expires: Optional[timedelta]

    @pydantic.validator("expires")
    def validate_expires(cls, v: timedelta) -> timedelta:
        if v < timedelta(0):
            raise ValueError("non-negative duration expected")
        return v


class Job(ModelConfigDefaults):
    """A job definition."""

    # XXX jugmac00 2012-12-17: working with Job's attributes could be
    # simplified if they would not be optional, but rather return e.g.
    # an empty list

    series: _Identifier
    architectures: List[_Identifier]
    run: Optional[StrictStr]
    environment: Optional[Dict[str, Optional[str]]]
    output: Optional[Output]
    snaps: Optional[List[StrictStr]]
    packages: Optional[List[StrictStr]]
    plugin: Optional[StrictStr]

    @pydantic.validator("architectures", pre=True)
    def validate_architectures(
        cls, v: Union[_Identifier, List[_Identifier]]
    ) -> List[_Identifier]:
        if isinstance(v, str):
            v = [v]
        return v


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


class Config(ModelConfigDefaults):
    """A .launchpad.yaml configuration file."""

    pipeline: List[List[_Identifier]]
    jobs: Dict[StrictStr, List[Job]]

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
