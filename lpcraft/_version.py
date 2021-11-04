# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

__all__ = [
    "version",
    "version_description",
]

import importlib.metadata
from configparser import ConfigParser
from pathlib import Path


def _get_version():
    try:
        return importlib.metadata.version("lpcraft")
    except importlib.metadata.PackageNotFoundError:
        setup_cfg_path = Path(__file__).parent.parent / "setup.cfg"
        if setup_cfg_path.exists():
            parser = ConfigParser()
            parser.read(setup_cfg_path)
            return parser.get("metadata", "version")
        else:
            raise RuntimeError("Cannot determine lpcraft version")


version = _get_version()
version_description = f"lpcraft, version {version}"
