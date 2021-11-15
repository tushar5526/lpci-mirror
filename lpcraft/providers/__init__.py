# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

__all__ = [
    "get_provider",
    "replay_logs",
]

import tempfile
from pathlib import Path

from craft_cli import emit
from craft_providers import Executor

from lpcraft.env import get_managed_environment_log_path
from lpcraft.providers._base import Provider
from lpcraft.providers._lxd import LXDProvider


def get_provider() -> Provider:
    """Get the configured or appropriate provider for the host OS."""
    return LXDProvider()


def replay_logs(instance: Executor) -> None:
    """Capture and re-emit log files from a provider instance."""
    tmp = tempfile.NamedTemporaryFile(delete=False, prefix="lpcraft-")
    tmp.close()
    local_log_path = Path(tmp.name)
    try:
        remote_log_path = get_managed_environment_log_path()

        try:
            instance.pull_file(
                source=remote_log_path, destination=local_log_path
            )
        except FileNotFoundError:
            emit.trace("No logs found in instance.")
            return

        emit.trace("Logs captured from managed instance:")
        with open(local_log_path) as local_log:
            for line in local_log:
                emit.trace(f":: {line.rstrip()}")
    finally:
        local_log_path.unlink()
