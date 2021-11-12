# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

from unittest.mock import Mock, patch

from craft_providers import Executor, bases
from craft_providers.actions import snap_installer

from lpcraft.providers._buildd import (
    SERIES_TO_BUILDD_IMAGE_ALIAS,
    LPCraftBuilddBaseConfiguration,
)
from lpcraft.providers.tests import ProviderBaseTestCase


class TestLPCraftBuilddBaseConfiguration(ProviderBaseTestCase):
    @patch("craft_providers.actions.snap_installer.inject_from_host")
    def test_setup_inject_from_host(self, mock_inject):
        mock_instance = Mock(spec=Executor)
        config = LPCraftBuilddBaseConfiguration(
            alias=SERIES_TO_BUILDD_IMAGE_ALIAS["focal"]
        )

        config.setup(executor=mock_instance)

        self.assertEqual("lpcraft-buildd-base-v0.0", config.compatibility_tag)
        mock_inject.assert_called_once_with(
            executor=mock_instance, snap_name="lpcraft", classic=True
        )

    @patch("craft_providers.actions.snap_installer.inject_from_host")
    def test_setup_inject_from_host_error(self, mock_inject):
        mock_instance = Mock(spec=Executor)
        mock_inject.side_effect = snap_installer.SnapInstallationError(
            brief="Boom"
        )
        config = LPCraftBuilddBaseConfiguration(
            alias=SERIES_TO_BUILDD_IMAGE_ALIAS["focal"]
        )

        with self.assertRaisesRegex(
            bases.BaseConfigurationError,
            r"^Failed to inject host lpcraft snap into target environment\.$",
        ) as raised:
            config.setup(executor=mock_instance)

        self.assertIsNotNone(raised.exception.__cause__)
