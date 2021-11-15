# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

from dataclasses import dataclass
from typing import List
from unittest.mock import ANY, call, patch

from craft_cli import CraftError
from testtools import TestCase

from lpcraft.main import main
from lpcraft.tests.fixtures import RecordingEmitterFixture


@dataclass
class _CommandResult:
    """The result of a command."""

    exit_code: int
    messages: List[str]
    errors: List[CraftError]


class CommandBaseTestCase(TestCase):
    def run_command(self, *args, **kwargs):
        with patch("sys.argv", ["lpcraft"] + list(args)):
            with RecordingEmitterFixture() as emitter:
                exit_code = main()
                return _CommandResult(
                    exit_code,
                    [
                        c.args[1]
                        for c in emitter.recorder.interactions
                        if c == call("message", ANY)
                    ],
                    [
                        c.args[1]
                        for c in emitter.recorder.interactions
                        if c == call("error", ANY)
                    ],
                )
