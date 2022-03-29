# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

import pytest
from craft_providers.bases.buildd import BuilddBaseAlias
from testtools import TestCase

from lpcraft.providers._buildd import LPCraftBuilddBaseConfiguration


class TestLPCraftBuilddBaseConfiguration(TestCase):
    def test_compare_configuration_with_other_type(self):
        """The configuration should only be comparable to its own type."""
        with pytest.raises(TypeError):
            "foo" == LPCraftBuilddBaseConfiguration(
                alias=BuilddBaseAlias.FOCAL,
            )
