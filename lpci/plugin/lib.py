"""`InternalPlugins` is the namespace for the internal plugins.

see https://pluggy.readthedocs.io/en/stable/#define-and-collect-hooks

Internal plugins provide the base functionality for lpci, which means that
these plugins cannot be removed without breaking the application.

The provided functionality can be extended by additional plugins.
"""

from __future__ import annotations

from lpci.config import Job, Snap
from lpci.plugin import hookimpl


class InternalPlugins:

    INTERPOLATES_RUN_COMMAND: bool = False

    def __init__(self, config: Job) -> None:
        self.config = config

    @hookimpl
    def lpci_install_packages(self) -> list[str]:
        if self.config.packages:
            return self.config.packages
        return []

    @hookimpl
    def lpci_install_snaps(self) -> list[Snap]:
        if self.config.snaps:
            return self.config.snaps
        return []
