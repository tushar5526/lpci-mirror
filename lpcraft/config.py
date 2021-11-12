# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

from pathlib import Path
from typing import Dict, List, Optional, Union

import pydantic
from pydantic import StrictStr

from lpcraft.utils import load_yaml


class ModelConfigDefaults(
    pydantic.BaseModel,
    extra=pydantic.Extra.forbid,
    frozen=True,
    alias_generator=lambda s: s.replace("_", "-"),
):
    """Define lpcraft's model defaults."""


class Job(ModelConfigDefaults):
    """A job definition."""

    series: StrictStr
    architectures: List[StrictStr]
    run: Optional[StrictStr]

    @pydantic.validator("architectures", pre=True)
    def validate_architectures(
        cls, v: Union[StrictStr, List[StrictStr]]
    ) -> List[StrictStr]:
        if isinstance(v, str):
            v = [v]
        return v


class Config(ModelConfigDefaults):
    """A .launchpad.yaml configuration file."""

    pipeline: List[StrictStr]
    jobs: Dict[StrictStr, Job]


def load(filename: str) -> Config:
    """Load config from the indicated file name."""
    path = Path(filename)
    content = load_yaml(path)
    return Config.parse_obj(content)
