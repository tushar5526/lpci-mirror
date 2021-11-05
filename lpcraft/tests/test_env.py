# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

from pathlib import Path

from fixtures import EnvironmentVariable
from testtools import TestCase

from lpcraft import env


class TestEnvironment(TestCase):
    def test_get_managed_environment_home_path(self):
        self.assertEqual(
            Path("/root"), env.get_managed_environment_home_path()
        )

    def test_get_managed_environment_project_path(self):
        self.assertEqual(
            Path("/root/project"), env.get_managed_environment_project_path()
        )

    def test_is_managed_mode(self):
        for mode, expected in (
            (None, False),
            ("y", True),
            ("n", False),
            ("1", True),
            ("0", False),
        ):
            with self.subTest(mode=mode):
                with EnvironmentVariable("LPCRAFT_MANAGED_MODE", mode):
                    self.assertIs(expected, env.is_managed_mode())
