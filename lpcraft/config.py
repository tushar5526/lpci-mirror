# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pydantic
from pydantic import StrictStr

from lpcraft.utils import load_yaml


class ModelConfigDefaults(
    pydantic.BaseModel,
    extra=pydantic.Extra.forbid,
    frozen=True,
    alias_generator=lambda s: s.replace("_", "-"),
    underscore_attrs_are_private=True,
):
    """Define lpcraft's model defaults."""


class Job(ModelConfigDefaults):
    """A job definition."""

    series: StrictStr
    architectures: List[StrictStr]
    run: Optional[StrictStr]
    environment: Optional[Dict[str, Optional[str]]]

    @pydantic.validator("architectures", pre=True)
    def validate_architectures(
        cls, v: Union[StrictStr, List[StrictStr]]
    ) -> List[StrictStr]:
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

    pipeline: List[StrictStr]
    jobs: Dict[StrictStr, List[Job]]

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
        content = load_yaml(path)
        return cls.parse_obj(content)
