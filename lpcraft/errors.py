# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

"""lpcraft errors."""

__all__ = [
    "CommandError",
    "YAMLError",
]

from typing import Any

from craft_cli import CraftError


class CommandError(CraftError):
    """Base exception for all error commands."""

    def __init__(self, message: str, retcode: int = 1):
        super().__init__(message, retcode=retcode)

    def __eq__(self, other: Any) -> bool:
        if type(self) != type(other):
            return NotImplemented
        return str(self) == str(other) and self.retcode == other.retcode


class YAMLError(CommandError):
    """Error reading YAML file."""
