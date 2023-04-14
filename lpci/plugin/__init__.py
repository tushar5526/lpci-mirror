# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

__all__ = ["NAME", "hookimpl"]

import pluggy

NAME = "lpci"  #: name of the hook

hookimpl = pluggy.HookimplMarker(NAME)  #: decorator to mark lpci plugin hooks
