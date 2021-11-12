# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

"""LXD build environment provider support for lpcraft."""

__all__ = [
    "LXDProvider",
]

import re
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, List

from craft_cli import emit
from craft_providers import bases, lxd

from lpcraft.env import get_managed_environment_project_path
from lpcraft.errors import CommandError
from lpcraft.providers._base import Provider
from lpcraft.providers._buildd import (
    SERIES_TO_BUILDD_IMAGE_ALIAS,
    LPCraftBuilddBaseConfiguration,
)
from lpcraft.utils import ask_user


class LXDProvider(Provider):
    """A LXD build environment provider for lpcraft.

    :param lxc: Optional lxc client to use.
    :param lxd_project: LXD project to use (default is lpcraft).
    :param lxd_remote: LXD remote to use (default is local).
    """

    def __init__(
        self,
        *,
        lxc: lxd.LXC = lxd.LXC(),
        lxd_project: str = "lpcraft",
        lxd_remote: str = "local",
    ) -> None:
        self.lxc = lxc
        self.lxd_project = lxd_project
        self.lxd_remote = lxd_remote

    def clean_project_environments(
        self, *, project_name: str, project_path: Path
    ) -> List[str]:
        """Clean up any environments created for a project.

        :param project_name: Name of project.
        :param project_path: Path to project.

        :return: List of containers deleted.
        """
        deleted: List[str] = []

        if not self.is_provider_available():
            return deleted

        inode = str(project_path.stat().st_ino)

        try:
            names = self.lxc.list_names(
                project=self.lxd_project, remote=self.lxd_remote
            )
        except lxd.LXDError as error:
            raise CommandError(str(error)) from error

        for name in names:
            if re.match(
                fr"^lpcraft-{re.escape(project_name)}-{re.escape(inode)}"
                fr"-.+-.+$",
                name,
            ):
                emit.trace(f"Deleting container {name!r}.")
                try:
                    self.lxc.delete(
                        instance_name=name,
                        force=True,
                        project=self.lxd_project,
                        remote=self.lxd_remote,
                    )
                except lxd.LXDError as error:
                    raise CommandError(str(error)) from error
                deleted.append(name)
            else:
                emit.trace(f"Not deleting container {name!r}.")

        return deleted

    @classmethod
    def ensure_provider_is_available(cls) -> None:
        """Ensure provider is available, prompting to install it if required.

        :raises CommandError: if provider is not available.
        """
        if not lxd.is_installed():
            if ask_user(
                "LXD is required, but not installed. Do you wish to install "
                "LXD and configure it with the defaults?",
                default=False,
            ):
                try:
                    lxd.install()
                except lxd.LXDInstallationError as error:
                    raise CommandError(
                        "Failed to install LXD. Visit "
                        "https://snapcraft.io/lxd for instructions on how to "
                        "install the LXD snap for your distribution."
                    ) from error
            else:
                raise CommandError(
                    "LXD is required, but not installed. Visit "
                    "https://snapcraft.io/lxd for instructions on how to "
                    "install the LXD snap for your distribution."
                )

        try:
            lxd.ensure_lxd_is_ready()
        except lxd.LXDError as error:
            raise CommandError(str(error)) from error

    @classmethod
    def is_provider_available(cls) -> bool:
        """Check if provider is installed and available for use.

        :return: True if installed.
        """
        return lxd.is_installed()

    @contextmanager
    def launched_environment(
        self,
        *,
        project_name: str,
        project_path: Path,
        series: str,
        architecture: str,
    ) -> Generator[lxd.LXDInstance, None, None]:
        """Launch environment for specified series and architecture.

        :param project_name: Name of project.
        :param project_path: Path to project.
        :param series: Distribution series name.
        :param architecture: Targeted architecture name.
        """
        alias = SERIES_TO_BUILDD_IMAGE_ALIAS[series]
        instance_name = self.get_instance_name(
            project_name=project_name,
            project_path=project_path,
            series=series,
            architecture=architecture,
        )
        environment = self.get_command_environment()
        try:
            image_remote = lxd.configure_buildd_image_remote()
        except lxd.LXDError as error:
            raise CommandError(str(error)) from error
        base_configuration = LPCraftBuilddBaseConfiguration(
            alias=alias, environment=environment, hostname=instance_name
        )

        try:
            instance = lxd.launch(
                name=instance_name,
                base_configuration=base_configuration,
                image_name=series,
                image_remote=image_remote,
                auto_clean=True,
                auto_create_project=True,
                map_user_uid=True,
                use_snapshots=True,
                project=self.lxd_project,
                remote=self.lxd_remote,
            )
        except (bases.BaseConfigurationError, lxd.LXDError) as error:
            raise CommandError(str(error)) from error

        instance.mount(
            host_source=project_path,
            target=get_managed_environment_project_path(),
        )

        try:
            yield instance
        finally:
            try:
                instance.unmount_all()
                instance.stop()
            except lxd.LXDError as error:
                raise CommandError(str(error)) from error
