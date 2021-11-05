# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

from testtools import TestCase

from lpcraft.providers import get_provider
from lpcraft.providers._lxd import LXDProvider


class TestGetProvider(TestCase):
    def test_default(self):
        self.assertIsInstance(get_provider(), LXDProvider)
