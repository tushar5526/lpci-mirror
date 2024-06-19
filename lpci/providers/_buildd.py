# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

"""Buildd-related code for lpci."""

__all__ = [
    "LPCIBuilddBaseConfiguration",
    "SERIES_TO_BUILDD_IMAGE_ALIAS",
]

from typing import Any

from craft_providers import bases

# Why can't we just pass a series name and be done with it?
SERIES_TO_BUILDD_IMAGE_ALIAS = {
    "xenial": bases.BuilddBaseAlias.XENIAL,
    "bionic": bases.BuilddBaseAlias.BIONIC,
    "focal": bases.BuilddBaseAlias.FOCAL,
    "jammy": bases.BuilddBaseAlias.JAMMY,
    "mantic": bases.BuilddBaseAlias.MANTIC,
    "noble": bases.BuilddBaseAlias.NOBLE,
    "oracular": bases.BuilddBaseAlias.ORACULAR,
    "devel": bases.BuilddBaseAlias.DEVEL,
}


class LPCIBuilddBaseConfiguration(bases.BuilddBase):
    """Base configuration for lpci.

    :cvar compatibility_tag: Tag/version for variant of build configuration
        and setup.  Any change to this version indicates that prior
        (versioned) instances are incompatible and must be cleaned.  As
        such, any new value should be unique by comparison with old values
        (e.g. incrementing).  lpci extends the buildd tag to include its
        own version indicator (.0) and namespace ("lpci").
    """

    compatibility_tag: str = f"lpci-{bases.BuilddBase.compatibility_tag}.0"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, LPCIBuilddBaseConfiguration):
            raise TypeError
        return (
            self.alias == other.alias
            and self._environment == other._environment
            and self._hostname == other._hostname
        )
