# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

from unittest.mock import call, patch

from craft_cli import CraftError, EmitterMode
from fixtures import MockPatch
from testtools import TestCase

from lpcraft._version import version_description as lpcraft_version
from lpcraft.main import main
from lpcraft.tests.fixtures import RecordingEmitterFixture


class TestMain(TestCase):
    def test_ok(self):
        # main() sets up the message handler and exits cleanly.
        mock_emit = self.useFixture(MockPatch("lpcraft.main.emit")).mock

        ret = main(["--version"])

        self.assertEqual(0, ret)
        mock_emit.init.assert_called_once_with(
            EmitterMode.NORMAL, "lpcraft", f"Starting {lpcraft_version}"
        )
        mock_emit.message.assert_called_once_with(lpcraft_version)
        mock_emit.ended_ok.assert_called_once_with()

    def test_bad_arguments(self):
        # main() exits appropriately if given bad arguments.
        mock_emit = self.useFixture(MockPatch("lpcraft.main.emit")).mock
        mock_argparse_print_message = self.useFixture(
            MockPatch("argparse.ArgumentParser._print_message")
        ).mock

        ret = main(["--nonexistent"])

        self.assertEqual(1, ret)
        # using `assert_called_with` is not possible as the message is
        # different depending whether pytest or coverage is driving the tests
        self.assertIn(
            "error: unrecognized arguments: --nonexistent\n",
            mock_argparse_print_message.call_args.args[0],
        )
        mock_emit.ended_ok.assert_called_once_with()

    @patch("lpcraft.main.run")
    def test_keyboard_interrupt(self, mock_run):
        mock_run.side_effect = KeyboardInterrupt()

        with RecordingEmitterFixture() as emitter:
            ret = main()

        self.assertEqual(1, ret)
        self.assertEqual(
            call("error", CraftError("Interrupted.")),
            emitter.recorder.interactions[0],
        )

    @patch("lpcraft.main.run")
    def test_handling_unexpected_exception(self, mock_run):
        self.useFixture(MockPatch("sys.argv", ["lpcraft"]))
        mock_run.side_effect = RuntimeError()

        with RecordingEmitterFixture() as emitter:
            ret = main()

        self.assertEqual(1, ret)
        self.assertEqual(
            call(
                "error", CraftError("lpcraft internal error: RuntimeError()")
            ),
            emitter.recorder.interactions[0],
        )

    def test_quiet_mode(self):
        # temporary test until cli API is set and a more meaningful test is
        # possible
        self.useFixture(MockPatch("sys.argv", ["lpcraft", "--version", "-q"]))

        with RecordingEmitterFixture() as emitter:
            main()

        # result is something like "lpcraft, version 0.0.1"
        self.assertIn(
            "lpcraft, version", emitter.recorder.interactions[0].args[1]
        )

    def test_verbose_mode(self):
        # temporary test until cli API is set and a more meaningful test is
        # possible
        self.useFixture(MockPatch("sys.argv", ["lpcraft", "--version", "-v"]))

        with RecordingEmitterFixture() as emitter:
            main()

        # result is something like "lpcraft, version 0.0.1"
        self.assertIn(
            "lpcraft, version", emitter.recorder.interactions[0].args[1]
        )

    def test_trace_mode(self):
        # temporary test until cli API is set and a more meaningful test is
        # possible
        self.useFixture(
            MockPatch("sys.argv", ["lpcraft", "--version", "--trace"])
        )

        with RecordingEmitterFixture() as emitter:
            main()

        # result is something like "lpcraft, version 0.0.1"
        self.assertIn(
            "lpcraft, version", emitter.recorder.interactions[0].args[1]
        )
