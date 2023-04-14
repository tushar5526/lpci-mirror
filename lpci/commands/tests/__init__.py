# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

from dataclasses import dataclass
from typing import List
from unittest.mock import ANY, call

from craft_cli import CraftError
from testtools import TestCase

from lpci.main import main
from lpci.tests.fixtures import RecordingEmitterFixture


@dataclass
class _CommandResult:
    """The result of a command."""

    exit_code: int
    messages: List[str]
    errors: List[CraftError]
    trace: List[str]


class CommandBaseTestCase(TestCase):
    def run_command(self, *args, **kwargs):
        with RecordingEmitterFixture() as emitter:
            exit_code = main(list(args))
            result = _CommandResult(
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
                [
                    c.args[1]
                    for c in emitter.recorder.interactions
                    if c == call("trace", ANY)
                ],
            )
            return result
