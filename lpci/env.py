# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

"""lpci environment utilities."""

from pathlib import Path


def get_non_root_user() -> str:
    return "_lpci"


def get_managed_environment_home_path() -> Path:
    """Path for home when running in managed environment."""
    return Path("/root")


def get_managed_environment_project_path() -> Path:
    """Path for project when running in managed environment."""
    return Path("/build/lpci/project")
