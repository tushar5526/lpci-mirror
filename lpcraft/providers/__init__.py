# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

__all__ = [
    "get_provider",
]

from lpcraft.providers._lxd import LXDProvider


def get_provider():
    """Get the configured or appropriate provider for the host OS."""
    return LXDProvider()
