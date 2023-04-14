# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

import os
import tempfile
from pathlib import Path
from unittest.mock import call

from craft_cli import messages
from fixtures import Fixture, MockPatchObject


class RecordingEmitter:
    """Record what is shown using the emitter."""

    def __init__(self):
        self.interactions = []

    def record(self, method_name, args, kwargs):
        """Record the method call and its specific parameters."""
        self.interactions.append(call(method_name, *args, **kwargs))


class RecordingEmitterFixture(Fixture):
    def _setUp(self):
        fd, filename = tempfile.mkstemp(prefix="emitter-logs")
        os.close(fd)
        self.addCleanup(os.unlink, filename)

        messages.TESTMODE = True
        messages.emit.init(
            messages.EmitterMode.QUIET,
            "test-emitter",
            "Hello",
            log_filepath=Path(filename),
        )
        self.addCleanup(messages.emit.ended_ok)

        self.recorder = recorder = RecordingEmitter()
        for method_name in ("message", "progress", "trace", "error"):
            self.useFixture(
                MockPatchObject(
                    messages.emit,
                    method_name,
                    lambda *a, method_name=method_name, **kw: recorder.record(
                        method_name, a, kw
                    ),
                )
            )
