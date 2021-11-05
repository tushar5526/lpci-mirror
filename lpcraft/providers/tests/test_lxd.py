# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

import re
from pathlib import Path
from unittest.mock import Mock, call

from craft_providers.bases import BaseConfigurationError, BuilddBaseAlias
from craft_providers.lxd import LXDError, LXDInstallationError
from fixtures import EnvironmentVariable, MockPatch

from lpcraft.errors import CommandError
from lpcraft.providers._lxd import LXDProvider
from lpcraft.providers.tests import MockLXC, ProviderBaseTestCase
from lpcraft.tests.fixtures import EmitterFixture

_base_path = (
    "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin"
)


class TestLXDProvider(ProviderBaseTestCase):
    def setUp(self):
        super().setUp()
        self.mock_lxc = self.useFixture(MockLXC()).mock
        self.mock_lxd_is_installed = self.useFixture(
            MockPatch("craft_providers.lxd.is_installed", return_value=True)
        ).mock
        self.mock_ask_user = self.useFixture(
            MockPatch("lpcraft.providers._lxd.ask_user", return_value=False)
        ).mock
        self.mock_lxd_install = self.useFixture(
            MockPatch("craft_providers.lxd.install")
        ).mock
        self.mock_configure_buildd_image_remote = self.useFixture(
            MockPatch(
                "craft_providers.lxd.configure_buildd_image_remote",
                return_value="buildd-remote",
            )
        ).mock
        self.mock_buildd_base_configuration = self.useFixture(
            MockPatch(
                "lpcraft.providers._lxd.LPCraftBuilddBaseConfiguration",
                autospec=True,
            )
        ).mock
        self.mock_lxd_launch = self.useFixture(
            MockPatch("craft_providers.lxd.launch", autospec=True)
        ).mock
        self.mock_path = Mock(spec=Path)
        self.mock_path.stat.return_value.st_ino = 12345
        self.emitter = self.useFixture(EmitterFixture())

    def test_clean_project_environments_without_lxd(self):
        self.mock_lxd_is_installed.return_value = False
        provider = LXDProvider(
            lxc=self.mock_lxc,
            lxd_project="test-project",
            lxd_remote="test-remote",
        )

        self.assertEqual(
            [],
            provider.clean_project_environments(
                project_name="my-project", project_path=self.mock_path
            ),
        )

        self.mock_lxd_is_installed.assert_called_once_with()
        self.mock_lxc.assert_not_called()

    def test_clean_project_environments_no_matches(self):
        self.mock_lxc.list_names.return_value = [
            "lpcraft-testproject-12345-focal-amd64"
        ]
        provider = LXDProvider(
            lxc=self.mock_lxc,
            lxd_project="test-project",
            lxd_remote="test-remote",
        )

        self.assertEqual(
            [],
            provider.clean_project_environments(
                project_name="my-project", project_path=self.mock_path
            ),
        )

        self.assertEqual(
            [call.list_names(project="test-project", remote="test-remote")],
            self.mock_lxc.mock_calls,
        )

    def test_clean_project_environments(self):
        self.mock_lxc.list_names.return_value = [
            "do-not-delete-me",
            "lpcraft-testproject-12345-focal-amd64",
            "lpcraft-my-project-12345--",
            "lpcraft-my-project-12345-focal-amd64",
            "lpcraft-my-project-12345-bionic-arm64",
            "lpcraft-my-project-123456--",
            "lpcraft_12345_focal_amd64",
        ]
        provider = LXDProvider(
            lxc=self.mock_lxc,
            lxd_project="test-project",
            lxd_remote="test-remote",
        )

        self.assertEqual(
            [
                "lpcraft-my-project-12345-focal-amd64",
                "lpcraft-my-project-12345-bionic-arm64",
            ],
            provider.clean_project_environments(
                project_name="my-project", project_path=self.mock_path
            ),
        )

        self.assertEqual(
            [
                call.list_names(project="test-project", remote="test-remote"),
                call.delete(
                    instance_name="lpcraft-my-project-12345-focal-amd64",
                    force=True,
                    project="test-project",
                    remote="test-remote",
                ),
                call.delete(
                    instance_name="lpcraft-my-project-12345-bionic-arm64",
                    force=True,
                    project="test-project",
                    remote="test-remote",
                ),
            ],
            self.mock_lxc.mock_calls,
        )

    def test_clean_project_environments_list_failure(self):
        error = LXDError(brief="Boom")
        self.mock_lxc.list_names.side_effect = error
        provider = LXDProvider(lxc=self.mock_lxc)

        with self.assertRaisesRegex(CommandError, r"Boom") as raised:
            provider.clean_project_environments(
                project_name="test", project_path=self.mock_path
            )

        self.assertIs(error, raised.exception.__cause__)

    def test_clean_project_environments_delete_failure(self):
        error = LXDError(brief="Boom")
        self.mock_lxc.list_names.return_value = [
            "lpcraft-test-12345-focal-amd64"
        ]
        self.mock_lxc.delete.side_effect = error
        provider = LXDProvider(lxc=self.mock_lxc)

        with self.assertRaisesRegex(CommandError, r"Boom") as raised:
            provider.clean_project_environments(
                project_name="test", project_path=self.mock_path
            )

        self.assertIs(error, raised.exception.__cause__)

    def test_ensure_provider_is_available_ok_when_installed(self):
        provider = LXDProvider()

        provider.ensure_provider_is_available()

    def test_ensure_provider_is_available_errors_when_user_declines(self):
        self.mock_lxd_is_installed.return_value = False
        provider = LXDProvider()

        self.assertRaisesRegex(
            CommandError,
            re.escape(
                "LXD is required, but not installed. Visit "
                "https://snapcraft.io/lxd for instructions on how to install "
                "the LXD snap for your distribution."
            ),
            provider.ensure_provider_is_available,
        )

        self.mock_ask_user.assert_called_once_with(
            "LXD is required, but not installed. Do you wish to install LXD "
            "and configure it with the defaults?",
            default=False,
        )

    def test_ensure_provider_is_available_errors_when_lxd_install_fails(self):
        error = LXDInstallationError("Boom")
        self.mock_lxd_is_installed.return_value = False
        self.mock_ask_user.return_value = True
        self.mock_lxd_install.side_effect = error
        provider = LXDProvider()

        with self.assertRaisesRegex(
            CommandError,
            re.escape(
                "Failed to install LXD. Visit https://snapcraft.io/lxd for "
                "instructions on how to install the LXD snap for your "
                "distribution."
            ),
        ) as raised:
            provider.ensure_provider_is_available()

        self.mock_ask_user.assert_called_once_with(
            "LXD is required, but not installed. Do you wish to install LXD "
            "and configure it with the defaults?",
            default=False,
        )
        self.assertIs(error, raised.exception.__cause__)

    def test_is_provider_available(self):
        for is_installed in (True, False):
            with self.subTest(is_installed=is_installed):
                self.mock_lxd_is_installed.return_value = is_installed
                provider = LXDProvider()

                self.assertIs(is_installed, provider.is_provider_available())

    def test_get_instance_name(self):
        provider = LXDProvider()

        self.assertEqual(
            "lpcraft-my-project-12345-focal-amd64",
            provider.get_instance_name(
                project_name="my-project",
                project_path=self.mock_path,
                series="focal",
                architecture="amd64",
            ),
        )

    def test_get_command_environment_minimal(self):
        self.useFixture(EnvironmentVariable("IGNORE", "sentinel"))
        self.useFixture(EnvironmentVariable("PATH", "not-using-host-path"))
        provider = LXDProvider()

        env = provider.get_command_environment()

        self.assertEqual(
            {
                "LPCRAFT_MANAGED_MODE": "1",
                "PATH": _base_path,
            },
            env,
        )

    def test_get_command_environment_with_proxy(self):
        self.useFixture(EnvironmentVariable("IGNORE", "sentinel"))
        self.useFixture(EnvironmentVariable("PATH", "not-using-host-path"))
        self.useFixture(EnvironmentVariable("http_proxy", "test-http-proxy"))
        self.useFixture(EnvironmentVariable("https_proxy", "test-https-proxy"))
        self.useFixture(EnvironmentVariable("no_proxy", "test-no-proxy"))
        provider = LXDProvider()

        env = provider.get_command_environment()

        self.assertEqual(
            {
                "LPCRAFT_MANAGED_MODE": "1",
                "PATH": _base_path,
                "http_proxy": "test-http-proxy",
                "https_proxy": "test-https-proxy",
                "no_proxy": "test-no-proxy",
            },
            env,
        )

    def test_launched_environment(self):
        expected_instance_name = "lpcraft-my-project-12345-focal-amd64"
        provider = LXDProvider()

        with provider.launched_environment(
            project_name="my-project",
            project_path=self.mock_path,
            series="focal",
            architecture="amd64",
        ) as instance:
            self.assertIsNotNone(instance)
            self.mock_configure_buildd_image_remote.assert_called_once_with()
            self.mock_buildd_base_configuration.assert_called_once_with(
                alias=BuilddBaseAlias.FOCAL,
                environment={"LPCRAFT_MANAGED_MODE": "1", "PATH": _base_path},
                hostname=expected_instance_name,
            )
            self.assertEqual(
                [
                    call(
                        name=expected_instance_name,
                        base_configuration=(
                            self.mock_buildd_base_configuration.return_value
                        ),
                        image_name="focal",
                        image_remote="buildd-remote",
                        auto_clean=True,
                        auto_create_project=True,
                        map_user_uid=True,
                        use_snapshots=True,
                        project="lpcraft",
                        remote="local",
                    ),
                    call().mount(
                        host_source=self.mock_path,
                        target=Path("/root/project"),
                    ),
                ],
                self.mock_lxd_launch.mock_calls,
            )
            self.mock_lxd_launch.reset_mock()

        self.assertEqual(
            [call().unmount_all(), call().stop()],
            self.mock_lxd_launch.mock_calls,
        )

    def test_launched_environment_launch_base_configuration_error(self):
        error = BaseConfigurationError(brief="Boom")
        self.mock_lxd_launch.side_effect = error
        provider = LXDProvider()

        with self.assertRaisesRegex(CommandError, r"Boom") as raised:
            with provider.launched_environment(
                project_name="my-project",
                project_path=self.mock_path,
                series="focal",
                architecture="amd64",
            ):
                pass

        self.assertIs(error, raised.exception.__cause__)

    def test_launched_environment_launch_lxd_error(self):
        error = LXDError(brief="Boom")
        self.mock_lxd_launch.side_effect = error
        provider = LXDProvider()

        with self.assertRaisesRegex(CommandError, r"Boom") as raised:
            with provider.launched_environment(
                project_name="my-project",
                project_path=self.mock_path,
                series="focal",
                architecture="amd64",
            ):
                pass

        self.assertIs(error, raised.exception.__cause__)

    def test_launched_environment_unmounts_and_stops_after_error(self):
        provider = LXDProvider()

        with self.assertRaisesRegex(RuntimeError, r"Boom"):
            with provider.launched_environment(
                project_name="my-project",
                project_path=self.mock_path,
                series="focal",
                architecture="amd64",
            ):
                self.mock_lxd_launch.reset_mock()
                raise RuntimeError("Boom")

        self.assertEqual(
            [call().unmount_all(), call().stop()],
            self.mock_lxd_launch.mock_calls,
        )

    def test_launched_environment_unmount_all_error(self):
        error = LXDError(brief="Boom")
        self.mock_lxd_launch.return_value.unmount_all.side_effect = error
        provider = LXDProvider()

        with self.assertRaisesRegex(CommandError, r"Boom") as raised:
            with provider.launched_environment(
                project_name="my-project",
                project_path=self.mock_path,
                series="focal",
                architecture="amd64",
            ):
                pass

        self.assertIs(error, raised.exception.__cause__)

    def test_launched_environment_stop_error(self):
        error = LXDError(brief="Boom")
        self.mock_lxd_launch.return_value.stop.side_effect = error
        provider = LXDProvider()

        with self.assertRaisesRegex(CommandError, r"Boom") as raised:
            with provider.launched_environment(
                project_name="my-project",
                project_path=self.mock_path,
                series="focal",
                architecture="amd64",
            ):
                pass

        self.assertIs(error, raised.exception.__cause__)
