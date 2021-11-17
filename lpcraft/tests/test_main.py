# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

import sys
from unittest.mock import patch

from craft_cli import EmitterMode
from fixtures import MockPatch
from testtools import TestCase

from lpcraft._version import version_description as lpcraft_version
from lpcraft.main import main
from lpcraft.tests.fixtures import RecordingEmitterFixture


class TestMain(TestCase):
    def test_ok(self):
        # main() sets up the message handler and exits cleanly.
        self.useFixture(MockPatch("sys.argv", ["lpcraft", "--version"]))
        mock_emit = self.useFixture(MockPatch("lpcraft.main.emit")).mock

        ret = main()

        self.assertEqual(0, ret)
        mock_emit.init.assert_called_once_with(
            EmitterMode.NORMAL, "lpcraft", f"Starting {lpcraft_version}"
        )
        mock_emit.message.assert_called_once_with(lpcraft_version)
        mock_emit.ended_ok.assert_called_once_with()

    def test_bad_arguments(self):
        # main() exits appropriately if given bad arguments.
        self.useFixture(MockPatch("sys.argv", ["lpcraft", "--nonexistent"]))
        mock_emit = self.useFixture(MockPatch("lpcraft.main.emit")).mock
        mock_argparse_print_message = self.useFixture(
            MockPatch("argparse.ArgumentParser._print_message")
        ).mock

        ret = main()

        self.assertEqual(1, ret)
        mock_argparse_print_message.assert_called_with(
            "lpcraft: error: unrecognized arguments: --nonexistent\n",
            sys.stderr,
        )
        mock_emit.ended_ok.assert_called_once_with()

    @patch("lpcraft.main.run")
    def test_keyboard_interrupt(self, mock_run):
        self.useFixture(MockPatch("sys.argv", ["lpcraft"]))
        mock_run.side_effect = KeyboardInterrupt()

        with RecordingEmitterFixture() as emitter:
            ret = main()

        self.assertEqual(1, ret)
        # cannot compare the results directly but only the str representation
        # see https://github.com/canonical/craft-cli/issues/40
        self.assertEqual(
            "call('error', CraftError('Interrupted.'))",
            str(emitter.recorder.interactions[0]),
        )

    @patch("lpcraft.main.run")
    def test_handling_unexpected_exception(self, mock_run):
        self.useFixture(MockPatch("sys.argv", ["lpcraft"]))
        mock_run.side_effect = RuntimeError()

        with RecordingEmitterFixture() as emitter:
            ret = main()

        self.assertEqual(1, ret)
        # cannot compare the results directly but only the str representation
        # see https://github.com/canonical/craft-cli/issues/40
        self.assertEqual(
            "call('error', CraftError('lpcraft internal error: RuntimeError()'))",  # noqa: E501
            str(emitter.recorder.interactions[0]),
        )
