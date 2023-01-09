# Copyright 2023 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

__all__ = [
    "get_current_branch",
    "get_current_remote_url",
]

import subprocess
from typing import Optional


def get_current_branch() -> Optional[str]:
    """Return the current Git branch name.

    If there is no current branch (e.g. after `git checkout --detach`), then
    return None.
    """
    current_branch = subprocess.run(
        ["git", "branch", "--show-current"],
        capture_output=True,
        check=True,
        text=True,
    ).stdout.rstrip("\n")
    if current_branch:
        return current_branch
    else:
        return None


def get_current_remote_url() -> Optional[str]:
    """Return the remote URL for the current Git branch.

    If there is no current branch, or if the current branch is not a
    remote-tracking branch, then return None.
    """
    current_branch = get_current_branch()
    if current_branch is None:
        return None
    current_remote = subprocess.run(
        ["git", "config", f"branch.{current_branch}.remote"],
        capture_output=True,
        check=True,
        text=True,
    ).stdout.rstrip("\n")
    if current_remote:
        return subprocess.run(
            ["git", "remote", "get-url", current_remote],
            capture_output=True,
            check=True,
            text=True,
        ).stdout.rstrip("\n")
    else:
        return None
