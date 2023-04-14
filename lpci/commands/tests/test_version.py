# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

from lpci.commands.tests import CommandBaseTestCase


class VersionTestCase(CommandBaseTestCase):
    def test_version_option(self):
        result = self.run_command("--version")
        self.assertEqual(0, result.exit_code)

    def test_version_subcommand(self):
        result = self.run_command("version")
        self.assertEqual(0, result.exit_code)

    def test_same_output(self):
        result1 = self.run_command("version")
        result2 = self.run_command("--version")
        self.assertEqual(result1.messages, result2.messages)
