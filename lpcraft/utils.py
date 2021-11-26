# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

__all__ = [
    "ask_user",
    "get_host_architecture",
    "load_yaml",
]

import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

import yaml

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


@lru_cache
def get_host_architecture() -> str:
    """Get the host architecture name, using dpkg's vocabulary."""
    # We may need a more complex implementation at some point in order to
    # run in non-dpkg-based environments.
    return subprocess.run(
        ["dpkg", "--print-architecture"],
        capture_output=True,
        check=True,
        universal_newlines=True,
    ).stdout.rstrip("\n")


def ask_user(prompt: str, default: bool = False) -> bool:
    """Ask user for a yes/no answer.

    If stdin is not a tty, or if the user returns an empty answer, return
    the default value.

    :return: True if answer starts with [yY], False if answer starts with
        [nN], otherwise the default.
    """
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
