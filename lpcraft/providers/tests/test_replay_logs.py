# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

from pathlib import Path
from shutil import copyfile
from unittest.mock import Mock

from craft_providers import Executor
from fixtures import TempDir

from lpcraft.commands.tests import CommandBaseTestCase
from lpcraft.providers import replay_logs
from lpcraft.tests.fixtures import RecordingEmitterFixture


class TestReplayLogs(CommandBaseTestCase):
    def test_cannot_pull_file(self):
        mock_instance = Mock(spec=Executor)
        mock_instance.pull_file.side_effect = FileNotFoundError()

        with RecordingEmitterFixture() as emitter:
            replay_logs(mock_instance)

        self.assertEqual(
            ("trace", "No logs found in instance."),
            emitter.recorder.interactions[0].args,
        )

    def test_replay_logs(self):
        self.tempdir = Path(self.useFixture(TempDir()).path)
        path = self.tempdir / "stub_remote_log_file"
        path.write_text("line1\nline2\nline3")

        def fake_pull_file(source, destination):
            # use injected `path` rather than source, which would be a
            # lpcraft.env.get_managed_environment_log_path, which is not
            # available in a test
            self.assertEqual(Path("/tmp/lpcraft.log"), Path(source))
            copyfile(path, destination)

        mock_instance = Mock(spec=Executor)
        mock_instance.pull_file = fake_pull_file

        with RecordingEmitterFixture() as emitter:
            replay_logs(mock_instance)

        self.assertEqual(
            ("trace", "Logs captured from managed instance:"),
            emitter.recorder.interactions[0].args,
        )
        self.assertEqual(
            ("trace", ":: line1"), emitter.recorder.interactions[1].args
        )
        self.assertEqual(
            ("trace", ":: line2"), emitter.recorder.interactions[2].args
        )
        self.assertEqual(
            ("trace", ":: line3"), emitter.recorder.interactions[3].args
        )
