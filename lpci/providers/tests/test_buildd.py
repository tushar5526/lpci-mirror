# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

import pytest
from craft_providers.bases.buildd import BuilddBaseAlias
from testtools import TestCase

from lpci.providers._buildd import LPCIBuilddBaseConfiguration


class TestLPCIBuilddBaseConfiguration(TestCase):
    def test_compare_configuration_with_other_type(self):
        """The configuration should only be comparable to its own type."""
        with pytest.raises(TypeError):
            "foo" == LPCIBuilddBaseConfiguration(
                alias=BuilddBaseAlias.FOCAL,
            )

    def test_series_to_buildd_image_alias(self):
        alias_mapping = {
            "16.04": BuilddBaseAlias.XENIAL.value,
            "18.04": BuilddBaseAlias.BIONIC.value,
            "20.04": BuilddBaseAlias.FOCAL.value,
            "22.04": BuilddBaseAlias.JAMMY.value,
            "22.10": BuilddBaseAlias.KINETIC.value,
            "23.04": BuilddBaseAlias.LUNAR.value,
            "devel": BuilddBaseAlias.DEVEL.value,
        }
        for k, v in alias_mapping.items():
            self.assertEqual(k, v)

        self.assertEqual(len(BuilddBaseAlias), len(alias_mapping))
