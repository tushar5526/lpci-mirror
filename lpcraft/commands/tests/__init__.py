# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

from dataclasses import dataclass
from typing import List

from craft_cli import CraftError
from fixtures import MockPatch
from testtools import TestCase

from lpcraft.main import main
from lpcraft.tests.fixtures import EmitterFixture


@dataclass
class _CommandResult:
    """The result of a command."""

    exit_code: int
    messages: List[str]
    errors: List[CraftError]


class CommandBaseTestCase(TestCase):
    def run_command(self, *args, **kwargs):
        with MockPatch("sys.argv", ["lpcraft"] + list(args)):
            with EmitterFixture() as emitter:
                exit_code = main()
                return _CommandResult(
                    exit_code,
                    [
                        call.args[0]
                        for call in emitter.emit_message.call_args_list
                    ],
                    [
                        call.args[0]
                        for call in emitter.emit_error.call_args_list
                    ],
                )
