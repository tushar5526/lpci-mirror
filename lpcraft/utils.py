# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

__all__ = [
    "ask_user",
    "load_yaml",
]

import sys
from pathlib import Path
from typing import Any, Dict

import yaml

from lpcraft.env import is_managed_mode
from lpcraft.errors import YAMLError


def load_yaml(path: Path) -> Dict[Any, Any]:
    """Return the content of a YAML file."""
    if not path.is_file():
        raise YAMLError(f"Couldn't find config file {str(path)!r}")
    try:
        with path.open("rb") as f:
            loaded = yaml.safe_load(f)
        if not isinstance(loaded, dict):
            raise YAMLError(
                f"Config file {str(path)!r} does not define a mapping"
            )
        return loaded
    except (yaml.error.YAMLError, OSError) as e:
        raise YAMLError(f"Failed to read/parse config file {str(path)!r}: {e}")


def ask_user(prompt: str, default: bool = False) -> bool:
    """Ask user for a yes/no answer.

    If stdin is not a tty, or if the user returns an empty answer, return
    the default value.

    :return: True if answer starts with [yY], False if answer starts with
        [nN], otherwise the default.
    """
    if is_managed_mode():
        raise RuntimeError("confirmation not yet supported in managed mode")

    if not sys.stdin.isatty():
        return default

    choices = " [Y/n]: " if default else " [y/N]: "
    reply = str(input(prompt + choices)).lower().strip()
    if reply:
        if reply[0] == "y":
            return True
        elif reply[0] == "n":
            return False
    return default
