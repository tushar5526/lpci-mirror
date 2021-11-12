# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

from fixtures import EnvironmentVariable, MockPatch
from testtools import TestCase

from lpcraft.utils import ask_user


class TestAskUser(TestCase):
    def setUp(self):
        super().setUp()
        self.mock_isatty = self.useFixture(MockPatch("sys.stdin.isatty")).mock
        self.mock_input = self.useFixture(
            MockPatch("lpcraft.utils.input")
        ).mock

    def test_defaults_with_tty(self):
        self.mock_isatty.return_value = True
        self.mock_input.return_value = ""

        self.assertIs(True, ask_user("prompt", default=True))
        self.mock_input.assert_called_once_with("prompt [Y/n]: ")
        self.mock_input.reset_mock()

        self.assertIs(False, ask_user("prompt", default=False))
        self.mock_input.assert_called_once_with("prompt [y/N]: ")

    def test_defaults_without_tty(self):
        self.mock_isatty.return_value = False

        self.assertIs(True, ask_user("prompt", default=True))
        self.assertIs(False, ask_user("prompt", default=False))

        self.mock_input.assert_not_called()

    def test_handles_input(self):
        for user_input, expected in (
            ("y", True),
            ("Y", True),
            ("yes", True),
            ("YES", True),
            ("n", False),
            ("N", False),
            ("no", False),
            ("NO", False),
        ):
            with self.subTest(user_input=user_input):
                self.mock_input.return_value = user_input

                self.assertIs(expected, ask_user("prompt"))

                self.mock_input.assert_called_once_with("prompt [y/N]: ")
                self.mock_input.reset_mock()

    def test_errors_in_managed_mode(self):
        self.useFixture(EnvironmentVariable("LPCRAFT_MANAGED_MODE", "1"))

        self.assertRaises(RuntimeError, ask_user, "prompt")
