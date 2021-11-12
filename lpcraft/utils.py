# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

__all__ = [
    "ask_user",
]

import sys

from lpcraft.env import is_managed_mode


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
