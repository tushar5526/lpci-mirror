# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

from pathlib import Path

from testtools import TestCase

from lpcraft import env


class TestEnvironment(TestCase):
    def test_get_managed_environment_home_path(self):
        self.assertEqual(
            Path("/root"), env.get_managed_environment_home_path()
        )

    def test_get_managed_environment_project_path(self):
        self.assertEqual(
            Path("/build/lpcraft/project"),
            env.get_managed_environment_project_path(),
        )
