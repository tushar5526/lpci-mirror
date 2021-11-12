# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

import os
from pathlib import Path
from unittest.mock import patch

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

    @patch.dict(os.environ, {})
    def test_is_managed_mode_unset(self):
        self.assertIs(False, env.is_managed_mode())

    @patch.dict(os.environ, {"LPCRAFT_MANAGED_MODE": "0"})
    def test_is_managed_mode_0(self):
        self.assertIs(False, env.is_managed_mode())

    @patch.dict(os.environ, {"LPCRAFT_MANAGED_MODE": "1"})
    def test_is_managed_mode_1(self):
        self.assertIs(True, env.is_managed_mode())
