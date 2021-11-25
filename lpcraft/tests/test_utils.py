# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

import io
import os
import re
from pathlib import Path
from unittest.mock import patch

from fixtures import TempDir
from systemfixtures import FakeProcesses
from testtools import TestCase

from lpcraft.errors import YAMLError
from lpcraft.utils import ask_user, get_host_architecture, load_yaml


class TestLoadYAML(TestCase):
    def setUp(self):
        super().setUp()
        self.tempdir = Path(self.useFixture(TempDir()).path)

    def test_success(self):
        path = self.tempdir / "testfile.yaml"
        path.write_text("foo: 123\n")
        self.assertEqual({"foo": 123}, load_yaml(path))

    def test_no_file(self):
        path = self.tempdir / "testfile.yaml"
        self.assertRaisesRegex(
            YAMLError,
            re.escape(f"Couldn't find config file {str(path)!r}"),
            load_yaml,
            path,
        )

    def test_directory(self):
        path = self.tempdir / "testfile.yaml"
        path.mkdir()
        self.assertRaisesRegex(
            YAMLError,
            re.escape(f"Couldn't find config file {str(path)!r}"),
            load_yaml,
            path,
        )

    def test_corrupted_format(self):
        path = self.tempdir / "testfile.yaml"
        path.write_text("foo: [1, 2\n")
        self.assertRaisesRegex(
            YAMLError,
            re.escape(
                f"Failed to read/parse config file {str(path)!r}: "
                "while parsing a flow sequence"
            ),
            load_yaml,
            path,
        )

    def test_not_mapping(self):
        path = self.tempdir / "testfile.yaml"
        path.write_text("- foo\n")
        self.assertRaisesRegex(
            YAMLError,
            re.escape(f"Config file {str(path)!r} does not define a mapping"),
            load_yaml,
            path,
        )


class TestGetHostArchitecture(TestCase):
    def setUp(self):
        super().setUp()
        self.addCleanup(get_host_architecture.cache_clear)

    def test_returns_dpkg_architecture(self):
        processes_fixture = self.useFixture(FakeProcesses())
        processes_fixture.add(
            lambda _: {"stdout": io.StringIO("ppc64el\n")}, name="dpkg"
        )

        self.assertEqual("ppc64el", get_host_architecture())

        self.assertEqual(
            [["dpkg", "--print-architecture"]],
            [proc._args["args"] for proc in processes_fixture.procs],
        )

    def test_caches(self):
        processes_fixture = self.useFixture(FakeProcesses())
        processes_fixture.add(
            lambda _: {"stdout": io.StringIO("amd64\n")}, name="dpkg"
        )

        self.assertEqual("amd64", get_host_architecture())
        self.assertEqual(1, len(processes_fixture.procs))

        self.assertEqual("amd64", get_host_architecture())
        self.assertEqual(1, len(processes_fixture.procs))


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
            ("x", False),  # anything outside y/n should return default
        ):
            with self.subTest(user_input=user_input):
                mock_input.return_value = user_input

                self.assertIs(expected, ask_user("prompt"))

                mock_input.assert_called_once_with("prompt [y/N]: ")
                mock_input.reset_mock()

    @patch.dict(os.environ, {"LPCRAFT_MANAGED_MODE": "1"})
    def test_errors_in_managed_mode(self):
        self.assertRaises(RuntimeError, ask_user, "prompt")
