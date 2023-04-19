# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

"""Build environment provider support for lpci."""

__all__ = [
    "Provider",
]

import os
import re
from abc import ABC, abstractmethod
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Generator, List, Optional

from craft_providers import bases, lxd
from pydantic import StrictStr


def sanitize_lxd_instance_name(name: str) -> str:
    """LXD instance names need to follow a certain pattern.

    Make sure we follow this pattern:
    https://linuxcontainers.org/lxd/docs/master/instances/
    """
    # There is no need to check for all edge cases, as e.g. we control how
    # the string starts and ends anyway.
    name = re.sub(r"[^A-Za-z0-9-]", "-", name)
    return name[:63]


class Provider(ABC):
    """A build environment provider for lpci."""

    @abstractmethod
    def clean_project_environments(
        self,
        *,
        project_name: str,
        project_path: Path,
        instances: Optional[List[StrictStr]] = None,
    ) -> List[str]:
        """Clean up any environments created for a project.

        :param project_name: Name of project.
        :param project_path: Path to project.
        :param instances: List of instance names to clean, optional.

        :return: List of containers deleted.

        All the environments created for the project will be deleted if
        the `instances` parameter is not passed.
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
        name = (
            f"lpci-{project_name}-{project_path.stat().st_ino}"
            f"-{series}-{architecture}"
        )
        return sanitize_lxd_instance_name(name)

    def get_command_environment(self) -> Dict[str, Optional[str]]:
        """Construct the required environment."""
        env = bases.buildd.default_command_environment()

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
        gpu_nvidia: bool = False,
        root: bool = False,
    ) -> Generator[lxd.LXDInstance, None, None]:
        """Launch environment for specified series and architecture.

        :param project_name: Name of project.
        :param project_path: Path to project.
        :param series: Distribution series name.
        :param architecture: Targeted architecture name.
        :param gpu_nvidia: If True, pass through an NVIDIA GPU from the host
            to the environment.
        """
