# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

from fixtures import Fixture, MockPatch


class EmitterFixture(Fixture):
    def _setUp(self):
        # Temporarily mock these until craft-cli grows additional testing
        # support.
        self.useFixture(MockPatch("craft_cli.emit.init"))
        self.emit_message = self.useFixture(
            MockPatch("craft_cli.emit.message")
        ).mock
        self.emit_progress = self.useFixture(
            MockPatch("craft_cli.emit.progress")
        ).mock
        self.emit_trace = self.useFixture(
            MockPatch("craft_cli.emit.trace")
        ).mock
        self.emit_error = self.useFixture(
            MockPatch("craft_cli.emit.error")
        ).mock
        self.emit_ended_ok = self.useFixture(
            MockPatch("craft_cli.emit.ended_ok")
        ).mock
