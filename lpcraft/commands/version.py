# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

from craft_cli import emit

from lpcraft._version import version_description as lpcraft_version


def version(args):
    """Show lpcraft's version number."""
    emit.message(lpcraft_version)
