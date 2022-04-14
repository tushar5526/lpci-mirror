# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

"""lpcraft environment utilities."""

from pathlib import Path


def get_managed_environment_home_path() -> Path:
    """Path for home when running in managed environment."""
    return Path("/root")


def get_managed_environment_project_path() -> Path:
    """Path for project when running in managed environment."""
    return get_managed_environment_home_path() / "lpcraft" / "project"
