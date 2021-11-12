# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

import os
from unittest.mock import patch

from testtools import TestCase

from lpcraft.utils import ask_user


class TestAskUser(TestCase):
    @patch("lpcraft.utils.input")
    @patch("sys.stdin.isatty")
    def test_defaults_with_tty(self, mock_isatty, mock_input):
        mock_isatty.return_value = True
        mock_input.return_value = ""

        self.assertIs(True, ask_user("prompt", default=True))
        mock_input.assert_called_once_with("prompt [Y/n]: ")
        mock_input.reset_mock()

        self.assertIs(False, ask_user("prompt", default=False))
        mock_input.assert_called_once_with("prompt [y/N]: ")

    @patch("lpcraft.utils.input")
    @patch("sys.stdin.isatty")
    def test_defaults_without_tty(self, mock_isatty, mock_input):
        mock_isatty.return_value = False

        self.assertIs(True, ask_user("prompt", default=True))
        self.assertIs(False, ask_user("prompt", default=False))

        mock_input.assert_not_called()

    @patch("lpcraft.utils.input")
    @patch("sys.stdin.isatty")
    def test_handles_input(self, mock_isatty, mock_input):
        mock_isatty.return_value = True

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
                mock_input.return_value = user_input

                self.assertIs(expected, ask_user("prompt"))

                mock_input.assert_called_once_with("prompt [y/N]: ")
                mock_input.reset_mock()

    @patch.dict(os.environ, {"LPCRAFT_MANAGED_MODE": "1"})
    def test_errors_in_managed_mode(self):
        self.assertRaises(RuntimeError, ask_user, "prompt")
