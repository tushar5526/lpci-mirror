# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

import re
from pathlib import Path
from typing import Optional
from unittest.mock import Mock, call, patch

from craft_providers.bases import BaseConfigurationError, BuilddBaseAlias
from craft_providers.lxd import LXC, LXDError, launch
from testtools import TestCase

from lpcraft.errors import CommandError
from lpcraft.providers._buildd import LPCraftBuilddBaseConfiguration
from lpcraft.providers._lxd import LXDProvider, _LXDLauncher
from lpcraft.providers.tests import FakeLXDInstaller
from lpcraft.tests.fixtures import RecordingEmitterFixture

_base_path = (
    "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin"
)


class TestLXDProvider(TestCase):
    def setUp(self):
        super().setUp()
        self.mock_path = Mock(spec=Path)
        self.mock_path.stat.return_value.st_ino = 12345
        self.useFixture(RecordingEmitterFixture())

    def makeLXDProvider(
        self,
        lxc: Optional[LXC] = None,
        can_install: bool = True,
        already_installed: bool = True,
        is_ready: bool = True,
        lxd_launcher: Optional[_LXDLauncher] = None,
        lxd_project: str = "test-project",
        lxd_remote: str = "test-remote",
    ) -> LXDProvider:
        if lxc is None:
            lxc = Mock(spec=LXC)
            lxc.remote_list.return_value = {}
        lxd_installer = FakeLXDInstaller(
            can_install=can_install,
            already_installed=already_installed,
            is_ready=is_ready,
        )
        if lxd_launcher is None:
            lxd_launcher = Mock(spec=launch)
        return LXDProvider(
            lxc=lxc,
            lxd_installer=lxd_installer,
            lxd_launcher=lxd_launcher,
            lxd_project=lxd_project,
            lxd_remote=lxd_remote,
        )

    def test_clean_project_environments_without_lxd(self):
        mock_lxc = Mock(spec=LXC)
        provider = self.makeLXDProvider(lxc=mock_lxc, already_installed=False)

        self.assertEqual(
            [],
            provider.clean_project_environments(
                project_name="my-project", project_path=self.mock_path
            ),
        )

        mock_lxc.assert_not_called()

    def test_clean_project_environments_no_matches(self):
        mock_lxc = Mock(spec=LXC)
        mock_lxc.list_names.return_value = [
            "lpcraft-testproject-12345-focal-amd64"
        ]
        provider = self.makeLXDProvider(lxc=mock_lxc)

        self.assertEqual(
            [],
            provider.clean_project_environments(
                project_name="my-project", project_path=self.mock_path
            ),
        )

        self.assertEqual(
            [call.list_names(project="test-project", remote="test-remote")],
            mock_lxc.mock_calls,
        )

    def test_clean_project_environments(self):
        mock_lxc = Mock(spec=LXC)
        mock_lxc.list_names.return_value = [
            "do-not-delete-me",
            "lpcraft-testproject-12345-focal-amd64",
            "lpcraft-my-project-12345--",
            "lpcraft-my-project-12345-focal-amd64",
            "lpcraft-my-project-12345-bionic-arm64",
            "lpcraft-my-project-123456--",
            "lpcraft_12345_focal_amd64",
        ]
        provider = self.makeLXDProvider(lxc=mock_lxc)

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
            mock_lxc.mock_calls,
        )

    def test_clean_project_environments_list_failure(self):
        error = LXDError(brief="Boom")
        mock_lxc = Mock(spec=LXC)
        mock_lxc.list_names.side_effect = error
        provider = self.makeLXDProvider(lxc=mock_lxc)

        with self.assertRaisesRegex(CommandError, r"Boom") as raised:
            provider.clean_project_environments(
                project_name="test", project_path=self.mock_path
            )

        self.assertIs(error, raised.exception.__cause__)

    def test_clean_project_environments_delete_failure(self):
        error = LXDError(brief="Boom")
        mock_lxc = Mock(spec=LXC)
        mock_lxc.list_names.return_value = ["lpcraft-test-12345-focal-amd64"]
        mock_lxc.delete.side_effect = error
        provider = self.makeLXDProvider(lxc=mock_lxc)

        with self.assertRaisesRegex(CommandError, r"Boom") as raised:
            provider.clean_project_environments(
                project_name="test", project_path=self.mock_path
            )

        self.assertIs(error, raised.exception.__cause__)

    def test_ensure_provider_is_available_ok_when_installed(self):
        provider = self.makeLXDProvider()

        provider.ensure_provider_is_available()

    @patch("lpcraft.providers._lxd.ask_user", return_value=False)
    def test_ensure_provider_is_available_errors_when_user_declines(
        self, mock_ask_user
    ):
        provider = self.makeLXDProvider(already_installed=False)

        self.assertRaisesRegex(
            CommandError,
            re.escape(
                "LXD is required, but not installed. Visit "
                "https://snapcraft.io/lxd for instructions on how to install "
                "the LXD snap for your distribution."
            ),
            provider.ensure_provider_is_available,
        )

        mock_ask_user.assert_called_once_with(
            "LXD is required, but not installed. Do you wish to install LXD "
            "and configure it with the defaults?",
            default=False,
        )

    @patch("lpcraft.providers._lxd.ask_user", return_value=True)
    def test_ensure_provider_is_available_errors_when_lxd_install_fails(
        self, mock_ask_user
    ):
        provider = self.makeLXDProvider(
            can_install=False, already_installed=False
        )

        with self.assertRaisesRegex(
            CommandError,
            re.escape(
                "Failed to install LXD. Visit https://snapcraft.io/lxd for "
                "instructions on how to install the LXD snap for your "
                "distribution."
            ),
        ):
            provider.ensure_provider_is_available()

        mock_ask_user.assert_called_once_with(
            "LXD is required, but not installed. Do you wish to install LXD "
            "and configure it with the defaults?",
            default=False,
        )

    def test_ensure_provider_is_available_errors_when_lxd_is_not_ready(self):
        provider = self.makeLXDProvider(is_ready=False)

        with self.assertRaisesRegex(CommandError, r"LXD is broken"):
            provider.ensure_provider_is_available()

    def test_is_provider_available(self):
        for is_installed in (True, False):
            with self.subTest(is_installed=is_installed):
                provider = self.makeLXDProvider(already_installed=is_installed)

                self.assertIs(is_installed, provider.is_provider_available())

    def test_get_instance_name(self):
        provider = self.makeLXDProvider()

        self.assertEqual(
            "lpcraft-my-project-12345-focal-amd64",
            provider.get_instance_name(
                project_name="my-project",
                project_path=self.mock_path,
                series="focal",
                architecture="amd64",
            ),
        )

    def test_get_sanitized_instance_name(self):
        # e.g. underscores are not allowed
        provider = self.makeLXDProvider()

        self.assertEqual(
            "lpcraft-my-project-12345-focal-amd64",
            provider.get_instance_name(
                project_name="my_project",
                project_path=self.mock_path,
                series="focal",
                architecture="amd64",
            ),
        )

    @patch("os.environ", {"IGNORE": "sentinel", "PATH": "not-using-host-path"})
    def test_get_command_environment_minimal(self):
        provider = self.makeLXDProvider()

        env = provider.get_command_environment()

        self.assertEqual({"PATH": _base_path}, env)

    @patch(
        "os.environ",
        {
            "IGNORE": "sentinel",
            "PATH": "not-using-host-path",
            "http_proxy": "test-http-proxy",
            "https_proxy": "test-https-proxy",
            "no_proxy": "test-no-proxy",
        },
    )
    def test_get_command_environment_with_proxy(self):
        provider = self.makeLXDProvider()

        env = provider.get_command_environment()

        self.assertEqual(
            {
                "PATH": _base_path,
                "http_proxy": "test-http-proxy",
                "https_proxy": "test-https-proxy",
                "no_proxy": "test-no-proxy",
            },
            env,
        )

    @patch("os.environ", {"PATH": "not-using-host-path"})
    def test_launched_environment(self):
        expected_instance_name = "lpcraft-my-project-12345-focal-amd64"
        mock_lxc = Mock(spec=LXC)
        mock_lxc.remote_list.return_value = {}
        mock_launcher = Mock(spec=launch)
        provider = self.makeLXDProvider(
            lxc=mock_lxc, lxd_launcher=mock_launcher
        )

        with provider.launched_environment(
            project_name="my-project",
            project_path=self.mock_path,
            series="focal",
            architecture="amd64",
        ) as instance:
            self.assertIsNotNone(instance)
            mock_lxc.remote_add.assert_called_once()
            self.assertEqual(
                [
                    call(
                        name=expected_instance_name,
                        base_configuration=LPCraftBuilddBaseConfiguration(
                            alias=BuilddBaseAlias.FOCAL,
                            environment={"PATH": _base_path},
                            hostname=expected_instance_name,
                        ),
                        image_name="focal",
                        image_remote="craft-com.ubuntu.cloud-buildd",
                        auto_clean=True,
                        auto_create_project=True,
                        map_user_uid=True,
                        use_snapshots=True,
                        project="test-project",
                        remote="test-remote",
                        lxc=mock_lxc,
                    ),
                    call().mount(
                        host_source=self.mock_path,
                        target=Path("/root/project"),
                    ),
                ],
                mock_launcher.mock_calls,
            )
            mock_launcher.reset_mock()

        self.assertEqual(
            [call().unmount_all(), call().stop()],
            mock_launcher.mock_calls,
        )

    def test_launched_environment_launch_base_configuration_error(self):
        error = BaseConfigurationError(brief="Boom")
        mock_launcher = Mock(
            "craft_providers.lxd.launch", autospec=True, side_effect=error
        )
        provider = self.makeLXDProvider(lxd_launcher=mock_launcher)

        with self.assertRaisesRegex(CommandError, r"Boom") as raised:
            with provider.launched_environment(
                project_name="my-project",
                project_path=self.mock_path,
                series="focal",
                architecture="amd64",
            ):
                pass  # pragma: no cover

        self.assertIs(error, raised.exception.__cause__)

    def test_launched_environment_launch_lxd_error(self):
        error = LXDError(brief="Boom")
        mock_launcher = Mock(
            "craft_providers.lxd.launch", autospec=True, side_effect=error
        )
        provider = self.makeLXDProvider(lxd_launcher=mock_launcher)
        with self.assertRaisesRegex(CommandError, r"Boom") as raised:
            with provider.launched_environment(
                project_name="my-project",
                project_path=self.mock_path,
                series="focal",
                architecture="amd64",
            ):
                pass  # pragma: no cover

        self.assertIs(error, raised.exception.__cause__)

    def test_launched_environment_unmounts_and_stops_after_error(self):
        mock_launcher = Mock(spec=launch)
        provider = self.makeLXDProvider(lxd_launcher=mock_launcher)
        with self.assertRaisesRegex(RuntimeError, r"Boom"):
            with provider.launched_environment(
                project_name="my-project",
                project_path=self.mock_path,
                series="focal",
                architecture="amd64",
            ):
                mock_launcher.reset_mock()
                raise RuntimeError("Boom")

        self.assertEqual(
            [call().unmount_all(), call().stop()],
            mock_launcher.mock_calls,
        )

    def test_launched_environment_unmount_all_error(self):
        error = LXDError(brief="Boom")
        mock_launcher = Mock(spec=launch)
        mock_launcher.return_value.unmount_all.side_effect = error
        provider = self.makeLXDProvider(lxd_launcher=mock_launcher)

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
        mock_launcher = Mock(spec=launch)
        mock_launcher.return_value.stop.side_effect = error
        provider = self.makeLXDProvider(lxd_launcher=mock_launcher)

        with self.assertRaisesRegex(CommandError, r"Boom") as raised:
            with provider.launched_environment(
                project_name="my-project",
                project_path=self.mock_path,
                series="focal",
                architecture="amd64",
            ):
                pass

        self.assertIs(error, raised.exception.__cause__)

    @patch("lpcraft.providers._lxd.lxd")
    def test_launched_environment_configure_buildd_image_remote_lxd_error(
        self, mock_lxd
    ):  # noqa: E501
        error = LXDError(brief="Boom")
        mock_lxd.configure_buildd_image_remote.side_effect = error
        # original behavior has to be restored as lxd is now a mock
        mock_lxd.LXDError = LXDError
        provider = self.makeLXDProvider()

        with self.assertRaisesRegex(CommandError, r"Boom") as raised:
            with provider.launched_environment(
                project_name="my-project",
                project_path=self.mock_path,
                series="focal",
                architecture="amd64",
            ):
                pass  # pragma: no cover

        self.assertIs(error, raised.exception.__cause__)
