# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

import io
from unittest.mock import call, patch

from craft_cli import CraftError, EmitterMode
from fixtures import MockPatch
from testtools import TestCase

from lpci._version import version_description as lpci_version
from lpci.main import main
from lpci.tests.fixtures import RecordingEmitterFixture


class TestMain(TestCase):
    def test_ok(self):
        # main() sets up the message handler and exits cleanly.
        mock_emit = self.useFixture(MockPatch("lpci.main.emit")).mock

        ret = main(["--version"])

        self.assertEqual(0, ret)
        mock_emit.init.assert_called_once_with(
            EmitterMode.BRIEF, "lpci", f"Starting {lpci_version}"
        )
        mock_emit.message.assert_called_once_with(lpci_version)
        mock_emit.ended_ok.assert_called_once_with()

    @patch("sys.stderr", new_callable=io.StringIO)
    def test_bad_arguments(self, mock_stderr):
        # main() exits appropriately if given bad arguments.
        mock_emit = self.useFixture(MockPatch("lpci.main.emit")).mock

        ret = main(["--nonexistent"])

        self.assertEqual(1, ret)
        self.assertIn(
            "Error: unrecognized arguments: --nonexistent\n",
            mock_stderr.getvalue(),
        )
        mock_emit.ended_ok.assert_called_once_with()

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_help(self, mock_stdout):
        mock_emit = self.useFixture(MockPatch("lpci.main.emit")).mock

        ret = main(["--help"])

        self.assertEqual(0, ret)
        self.assertIn("Usage:\n", mock_stdout.getvalue())
        mock_emit.ended_ok.assert_called_once_with()

    @patch("lpci.commands.run.RunCommand.run")
    def test_keyboard_interrupt(self, mock_run):
        mock_run.side_effect = KeyboardInterrupt()

        with RecordingEmitterFixture() as emitter:
            ret = main([])

        self.assertEqual(1, ret)
        self.assertEqual(
            call("error", CraftError("Interrupted.")),
            emitter.recorder.interactions[-1],
        )

    @patch("lpci.commands.run.RunCommand.run")
    def test_handling_unexpected_exception(self, mock_run):
        self.useFixture(MockPatch("sys.argv", ["lpci"]))
        mock_run.side_effect = RuntimeError()

        with RecordingEmitterFixture() as emitter:
            ret = main()

        self.assertEqual(1, ret)
        self.assertEqual(
            call("error", CraftError("lpci internal error: RuntimeError()")),
            emitter.recorder.interactions[-1],
        )

    @patch("lpci.commands.run.RunCommand.run")
    def test_debug_shell_mode_exception(self, mock_run):
        self.useFixture(MockPatch("sys.argv", ["lpci", "--debug-shell"]))
        mock_run.side_effect = RuntimeError()

        with RecordingEmitterFixture() as emitter:
            ret = main()

        self.assertEqual(1, ret)
        self.assertEqual(
            call(
                "progress",
                "Launching debug shell on build environment...",
                permanent=True,
            ),
            emitter.recorder.interactions[-2],
        )
        self.assertEqual(
            call("error", CraftError("lpci internal error: RuntimeError()")),
            emitter.recorder.interactions[-1],
        )

    @patch("lpci.commands.run.RunCommand.run")
    def test_debug_shell_mode_craft_exception(self, mock_run):
        self.useFixture(MockPatch("sys.argv", ["lpci", "--debug-shell"]))
        mock_run.side_effect = CraftError(
            "lpci internal error: RuntimeError()"
        )

        with RecordingEmitterFixture() as emitter:
            ret = main()

        self.assertEqual(1, ret)
        self.assertEqual(
            call(
                "progress",
                "Launching debug shell on build environment...",
                permanent=True,
            ),
            emitter.recorder.interactions[-2],
        )
        self.assertEqual(
            call("error", CraftError("lpci internal error: RuntimeError()")),
            emitter.recorder.interactions[-1],
        )

    def test_quiet_mode(self):
        # temporary test until cli API is set and a more meaningful test is
        # possible
        self.useFixture(MockPatch("sys.argv", ["lpci", "--version", "-q"]))

        with RecordingEmitterFixture() as emitter:
            main()

        # result is something like "lpci, version 0.0.1"
        self.assertIn(
            "lpci, version", emitter.recorder.interactions[-1].args[1]
        )

    def test_verbose_mode(self):
        # temporary test until cli API is set and a more meaningful test is
        # possible
        self.useFixture(MockPatch("sys.argv", ["lpci", "--version", "-v"]))

        with RecordingEmitterFixture() as emitter:
            main()

        # result is something like "lpci, version 0.0.1"
        self.assertIn(
            "lpci, version", emitter.recorder.interactions[-1].args[1]
        )

    def test_trace_mode(self):
        # temporary test until cli API is set and a more meaningful test is
        # possible
        self.useFixture(
            MockPatch("sys.argv", ["lpci", "--version", "--trace"])
        )

        with RecordingEmitterFixture() as emitter:
            main()

        # result is something like "lpci, version 0.0.1"
        self.assertIn(
            "lpci, version", emitter.recorder.interactions[-1].args[1]
        )
