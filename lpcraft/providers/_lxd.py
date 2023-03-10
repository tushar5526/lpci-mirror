# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

"""LXD build environment provider support for lpcraft."""

__all__ = [
    "LXDProvider",
]

import re
import subprocess
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator, List, Optional, Protocol

from craft_cli import emit
from craft_providers import Base, bases, lxd
from pydantic import StrictStr

from lpcraft.env import (
    get_managed_environment_home_path,
    get_managed_environment_project_path,
)
from lpcraft.errors import CommandError
from lpcraft.providers._base import Provider, sanitize_lxd_instance_name
from lpcraft.providers._buildd import (
    SERIES_TO_BUILDD_IMAGE_ALIAS,
    LPCraftBuilddBaseConfiguration,
)
from lpcraft.utils import ask_user

_lxc_client = lxd.LXC()


class _LXDInstaller(Protocol):
    def install(self) -> str:
        """Install LXD."""

    def is_installed(self) -> bool:
        """Check if LXD is installed (and found on PATH)."""

    def ensure_lxd_is_ready(self) -> None:
        """Ensure LXD is ready for use."""


class _LXDLauncher(Protocol):
    def __call__(
        self,
        name: str,
        *,
        base_configuration: Base,
        image_name: str,
        image_remote: str,
        auto_clean: bool = False,
        auto_create_project: bool = False,
        ephemeral: bool = False,
        map_user_uid: bool = False,
        use_base_instance: bool = False,
        project: str = "default",
        remote: str = "local",
        lxc: lxd.LXC = _lxc_client,
    ) -> lxd.LXDInstance:
        """Create, start, and configure a LXD instance."""


class _RealLXDInstaller:
    """A LXD installer implementation using craft-providers.

    This only exists because mypy doesn't support using modules as subtypes
    of protocols; see https://github.com/python/mypy/issues/5018.
    """

    def install(self) -> str:
        """Install LXD."""
        return lxd.install()  # pragma: no cover

    def is_installed(self) -> bool:
        """Check if LXD is installed (and found on PATH)."""
        return lxd.is_installed()  # pragma: no cover

    def ensure_lxd_is_ready(self) -> None:
        """Ensure LXD is ready for use."""
        return lxd.ensure_lxd_is_ready()  # pragma: no cover


class LXDProvider(Provider):
    """A LXD build environment provider for lpcraft.

    :param lxc: Optional lxc client to use.
    :param lxd_installer: LXD installer to use (default is
        craft_providers.lxd).
    :param lxd_launcher: LXD launcher to use (default is
        craft_providers.lxd.launch).
    :param lxd_project: LXD project to use (default is "lpcraft").
    :param lxd_remote: LXD remote to use (default is "local").
    """

    def __init__(
        self,
        *,
        lxc: lxd.LXC = _lxc_client,
        lxd_installer: _LXDInstaller = _RealLXDInstaller(),
        lxd_launcher: _LXDLauncher = lxd.launch,
        lxd_project: str = "lpcraft",
        lxd_remote: str = "local",
    ) -> None:
        self.lxc = lxc
        self.lxd_installer = lxd_installer
        self.lxd_launcher = lxd_launcher
        self.lxd_project = lxd_project
        self.lxd_remote = lxd_remote

    def clean_project_environments(
        self,
        *,
        project_name: str,
        project_path: Path,
        instances: Optional[List[StrictStr]] = None,
    ) -> List[str]:
        """Clean up the environments created for a project.

        :param project_name: Name of project.
        :param project_path: Path to project.
        :param instances: The list of instance names to delete, optional.

        :return: List of containers deleted.

        All the environments created for the project will be deleted if
        the `instances` parameter is not passed.
        """
        deleted: List[str] = []

        if not self.is_provider_available():
            return deleted

        inode = str(project_path.stat().st_ino)

        if not instances:
            try:
                instances = self.lxc.list_names(
                    project=self.lxd_project, remote=self.lxd_remote
                )
            except lxd.LXDError as error:
                raise CommandError(str(error)) from error

        project_name = sanitize_lxd_instance_name(project_name)
        for instance in instances:
            if re.match(
                rf"^lpcraft-{re.escape(project_name)}-{re.escape(inode)}"
                rf"-.+-.+$",
                instance,
            ):
                emit.trace(f"Deleting container {instance!r}.")
                try:
                    self.lxc.delete(
                        instance_name=instance,
                        force=True,
                        project=self.lxd_project,
                        remote=self.lxd_remote,
                    )
                except lxd.LXDError as error:
                    raise CommandError(str(error)) from error
                deleted.append(instance)
            else:
                emit.trace(f"Not deleting container {instance!r}.")

        return deleted

    def ensure_provider_is_available(self) -> None:
        """Ensure provider is available, prompting to install it if required.

        :raises CommandError: if provider is not available.
        """
        if not self.lxd_installer.is_installed():
            if ask_user(
                "LXD is required, but not installed. Do you wish to install "
                "LXD and configure it with the defaults?",
                default=False,
            ):
                try:
                    self.lxd_installer.install()
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
            self.lxd_installer.ensure_lxd_is_ready()
        except lxd.LXDError as error:
            raise CommandError(str(error)) from error

    def is_provider_available(self) -> bool:
        """Check if provider is installed and available for use.

        :return: True if installed.
        """
        return self.lxd_installer.is_installed()

    def _internal_execute_run(
        self,
        instance: lxd.LXDInstance,
        instance_name: str,
        command: List[str],
        **kwargs: Any,
    ) -> Any:  # LXC.exec has no return type annotation
        """Execute an internal command using subprocess.run().

        This is like LXDInstance.execute_run(), but we drop down to
        LXC.exec() for easier testability: this approach means that we don't
        have to cause all our (many) tests that look at
        LXDInstance.execute_run's call list to make assertions about
        internal details of the provider.

        :param instance: Instance to execute in.
        :param instance_name: Name of instance to execute in.
        :param command: Command to execute.
        :param kwargs: Keyword args to pass to subprocess.run().

        :returns: Completed process.

        :raises subprocess.CalledProcessError: if command fails and check is
            True.
        """
        return instance.lxc.exec(
            instance_name=instance_name,
            command=command,
            project=self.lxd_project,
            remote=self.lxd_remote,
            runner=subprocess.run,
            **kwargs,
        )

    @contextmanager
    def launched_environment(
        self,
        *,
        project_name: str,
        project_path: Path,
        series: str,
        architecture: str,
        gpu_nvidia: bool = False,
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
            image_remote = lxd.get_remote_image(alias.value)
        except lxd.LXDError as error:
            raise CommandError(str(error)) from error
        base_configuration = LPCraftBuilddBaseConfiguration(
            alias=alias, environment=environment, hostname=instance_name
        )

        if self.lxd_project not in self.lxc.project_list(self.lxd_remote):
            self.lxc.project_create(
                project=self.lxd_project, remote=self.lxd_remote
            )
        # Copy the default profile from the default project and adjust it
        # for our needs.  Unfortunately we have to edit the default profile
        # in our project since there's no way to get craft-providers to use
        # a different profile, but at least the profile is within the scope
        # of the project so shouldn't affect other users of LXD.
        profile = self.lxc.profile_show(
            profile="default", project="default", remote=self.lxd_remote
        )
        if gpu_nvidia:
            profile["config"]["nvidia.runtime"] = "true"
            profile["devices"]["gpu"] = {"type": "gpu"}
        else:
            profile["config"].pop("nvidia.runtime", None)
            profile["devices"].pop("gpu", None)
        self.lxc.profile_edit(
            profile="default",
            config=profile,
            project=self.lxd_project,
            remote=self.lxd_remote,
        )

        try:
            instance = self.lxd_launcher(
                name=instance_name,
                base_configuration=base_configuration,
                image_name=series,
                image_remote=image_remote.remote_name,
                auto_clean=True,
                auto_create_project=True,
                map_user_uid=True,
                use_base_instance=True,
                project=self.lxd_project,
                remote=self.lxd_remote,
                lxc=self.lxc,
            )
        except (bases.BaseConfigurationError, lxd.LXDError) as error:
            raise CommandError(str(error)) from error

        managed_project_path = get_managed_environment_project_path()
        try:
            tmp_project_path = (
                get_managed_environment_home_path() / "tmp-project"
            )
            instance.mount(host_source=project_path, target=tmp_project_path)
            try:
                self._internal_execute_run(
                    instance,
                    instance_name,
                    ["rm", "-rf", managed_project_path.as_posix()],
                    check=True,
                )
                self._internal_execute_run(
                    instance,
                    instance_name,
                    ["mkdir", "-p", managed_project_path.parent.as_posix()],
                    check=True,
                )
                self._internal_execute_run(
                    instance,
                    instance_name,
                    [
                        "cp",
                        "-a",
                        tmp_project_path.as_posix(),
                        managed_project_path.as_posix(),
                    ],
                    check=True,
                )
            except subprocess.CalledProcessError as error:
                raise CommandError(str(error)) from error
            finally:
                instance.unmount(target=tmp_project_path)

            yield instance
        finally:
            try:
                self._internal_execute_run(
                    instance,
                    instance_name,
                    ["rm", "-rf", managed_project_path.as_posix()],
                    check=True,
                )
                instance.unmount_all()
                instance.stop()
            except lxd.LXDError as error:
                raise CommandError(str(error)) from error
