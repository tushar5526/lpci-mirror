# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

__all__ = [
    "version",
    "version_description",
]

import importlib.metadata

version = importlib.metadata.version("lpcraft")
version_description = f"lpcraft, version {version}"
