# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

"""lpcraft errors."""

__all__ = [
    "CommandError",
]


class CommandError(Exception):
    """Base exception for all error commands."""

    def __init__(self, message):
        super().__init__(message)
