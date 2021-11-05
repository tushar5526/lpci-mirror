# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

"""Buildd-related code for lpcraft."""

__all__ = [
    "LPCraftBuilddBaseConfiguration",
    "SERIES_TO_BUILDD_IMAGE_ALIAS",
]

from typing import Optional

from craft_providers import Executor, bases
from craft_providers.actions import snap_installer

# Why can't we just pass a series name and be done with it?
SERIES_TO_BUILDD_IMAGE_ALIAS = {
    "xenial": bases.BuilddBaseAlias.XENIAL,
    "bionic": bases.BuilddBaseAlias.BIONIC,
    "focal": bases.BuilddBaseAlias.FOCAL,
}


class LPCraftBuilddBaseConfiguration(bases.BuilddBase):
    """Base configuration for lpcraft.

    :cvar compatibility_tag: Tag/version for variant of build configuration
        and setup.  Any change to this version indicates that prior
        (versioned) instances are incompatible and must be cleaned.  As
        such, any new value should be unique by comparison with old values
        (e.g. incrementing).  lpcraft extends the buildd tag to include its
        own version indicator (.0) and namespace ("lpcraft").
    """

    compatibility_tag: str = f"lpcraft-{bases.BuilddBase.compatibility_tag}.0"

    def _setup_lpcraft(self, *, executor: Executor) -> None:
        """Install lpcraft in target environment.

        The default behaviour is to inject the host snap into the target
        environment.

        :raises BaseConfigurationError: on error.
        """
        try:
            snap_installer.inject_from_host(
                executor=executor, snap_name="lpcraft", classic=True
            )
        except snap_installer.SnapInstallationError as error:
            raise bases.BaseConfigurationError(
                brief=(
                    "Failed to inject host lpcraft snap into target "
                    "environment."
                )
            ) from error

    def setup(
        self,
        *,
        executor: Executor,
        retry_wait: float = 0.25,
        timeout: Optional[float] = None,
    ) -> None:
        """Prepare base instance for use by the application.

        In addition to the guarantees provided by buildd, the lpcraft snap
        is installed.

        :param executor: Executor for target container.
        :param retry_wait: Duration to sleep() between status checks (if
            required).
        :param timeout: Timeout in seconds.

        :raises BaseCompatibilityError: if the instance is incompatible.
        :raises BaseConfigurationError: on any other unexpected error.
        """
        super().setup(
            executor=executor, retry_wait=retry_wait, timeout=timeout
        )
        self._setup_lpcraft(executor=executor)
