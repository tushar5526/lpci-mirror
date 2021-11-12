# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

"""Build environment provider support for lpcraft."""

__all__ = [
    "Provider",
]

import os
from abc import ABC, abstractmethod
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Generator, List, Optional

from craft_providers import bases, lxd


class Provider(ABC):
    """A build environment provider for lpcraft."""

    @abstractmethod
    def clean_project_environments(
        self, *, project_name: str, project_path: Path
    ) -> List[str]:
        """Clean up any environments created for a project.

        :param project_name: Name of project.
        :param project_path: Path to project.

        :return: List of containers deleted.
        """

    @abstractmethod
    def ensure_provider_is_available(self) -> None:
        """Ensure provider is available, prompting to install it if required.

        :raises CommandError: if provider is not available.
        """

    @abstractmethod
    def is_provider_available(self) -> bool:
        """Check if provider is installed and available for use.

        :return: True if installed.
        """

    def get_instance_name(
        self,
        *,
        project_name: str,
        project_path: Path,
        series: str,
        architecture: str,
    ) -> str:
        """Get the name for an instance using the given parameters.

        :param project_name: Name of project.
        :param project_path: Path to project.
        :param series: Distribution series name.
        :param architecture: Targeted architecture name.
        """
        return (
            f"lpcraft-{project_name}-{project_path.stat().st_ino}"
            f"-{series}-{architecture}"
        )

    def get_command_environment(self) -> Dict[str, Optional[str]]:
        """Construct the required environment."""
        env = bases.buildd.default_command_environment()
        env["LPCRAFT_MANAGED_MODE"] = "1"

        # Pass through host environment that target may need.
        for env_key in ("http_proxy", "https_proxy", "no_proxy"):
            if env_key in os.environ:
                env[env_key] = os.environ[env_key]

        return env

    @abstractmethod
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
