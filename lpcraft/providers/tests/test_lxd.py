# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

import re
import subprocess
from pathlib import Path
from typing import Any, AnyStr, List
from unittest.mock import ANY, Mock, call, patch

from craft_providers.bases import BaseConfigurationError, BuilddBaseAlias
from craft_providers.lxd import LXC, LXDError, launch
from testtools import TestCase

from lpcraft.errors import CommandError
from lpcraft.providers._buildd import LPCraftBuilddBaseConfiguration
from lpcraft.providers.tests import makeLXDProvider
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

    def test_clean_project_environments_without_lxd(self):
        mock_lxc = Mock(spec=LXC)
        provider = makeLXDProvider(lxc=mock_lxc, already_installed=False)

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
        provider = makeLXDProvider(lxc=mock_lxc)

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

    def test_clean_project_environments_project_name_requires_sanitizing(self):
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
        provider = makeLXDProvider(lxc=mock_lxc)

        self.assertEqual(
            [
                "lpcraft-my-project-12345-focal-amd64",
                "lpcraft-my-project-12345-bionic-arm64",
            ],
            provider.clean_project_environments(
                project_name="my.project", project_path=self.mock_path
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
        provider = makeLXDProvider(lxc=mock_lxc)

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
        provider = makeLXDProvider(lxc=mock_lxc)

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
        provider = makeLXDProvider(lxc=mock_lxc)

        with self.assertRaisesRegex(CommandError, r"Boom") as raised:
            provider.clean_project_environments(
                project_name="test", project_path=self.mock_path
            )

        self.assertIs(error, raised.exception.__cause__)

    def test_clean_project_environments_deletes_all_project_envs_when_instances_empty(  # noqa: E501
        self,
    ):
        mock_lxc = Mock(spec=LXC)
        instances = [
            "lpcraft-my-project-12345-focal-amd64",
            "lpcraft-my-project-12345-bionic-arm64",
        ]
        mock_lxc.list_names.return_value = instances
        provider = makeLXDProvider(lxc=mock_lxc)

        self.assertEqual(
            [
                "lpcraft-my-project-12345-focal-amd64",
                "lpcraft-my-project-12345-bionic-arm64",
            ],
            provider.clean_project_environments(
                project_name="my-project",
                project_path=self.mock_path,
                instances=[],
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

    def test_clean_project_environments_deletes_only_the_specified_project_instances(  # noqa: E501
        self,
    ):
        mock_lxc = Mock(spec=LXC)
        instances = [
            "lpcraft-my-project-12345-focal-amd64",
            "lpcraft-my-project-12345-bionic-arm64",
        ]
        mock_lxc.list_names.return_value = instances
        provider = makeLXDProvider(lxc=mock_lxc)

        self.assertEqual(
            [
                "lpcraft-my-project-12345-bionic-arm64",
            ],
            provider.clean_project_environments(
                project_name="my-project",
                project_path=self.mock_path,
                instances=[
                    "lpcraft-my-project-12345-bionic-arm64",
                ],
            ),
        )
        self.assertEqual(
            [
                call.delete(
                    instance_name="lpcraft-my-project-12345-bionic-arm64",
                    force=True,
                    project="test-project",
                    remote="test-remote",
                ),
            ],
            mock_lxc.mock_calls,
        )

    def test_clean_project_environments_deletes_only_the_project_instances_from_the_given_instances(  # noqa: E501
        self,
    ):
        mock_lxc = Mock(spec=LXC)
        provider = makeLXDProvider(lxc=mock_lxc)
        instances = [
            "lpcraft-my-project-12345-focal-amd64",
            "lpcraft-my-project-12345-bionic-arm64",
            "do-not-delete-me",
            "lpcraft-testproject-12345-focal-amd64",
        ]

        self.assertEqual(
            [
                "lpcraft-my-project-12345-focal-amd64",
                "lpcraft-my-project-12345-bionic-arm64",
            ],
            provider.clean_project_environments(
                project_name="my-project",
                project_path=self.mock_path,
                instances=instances,
            ),
        )
        self.assertEqual(
            [
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

    def test_ensure_provider_is_available_ok_when_installed(self):
        provider = makeLXDProvider()

        provider.ensure_provider_is_available()

    @patch("lpcraft.providers._lxd.ask_user", return_value=False)
    def test_ensure_provider_is_available_errors_when_user_declines(
        self, mock_ask_user
    ):
        provider = makeLXDProvider(already_installed=False)

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
        provider = makeLXDProvider(can_install=False, already_installed=False)

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
        provider = makeLXDProvider(is_ready=False)

        with self.assertRaisesRegex(CommandError, r"LXD is broken"):
            provider.ensure_provider_is_available()

    def test_is_provider_available(self):
        for is_installed in (True, False):
            with self.subTest(is_installed=is_installed):
                provider = makeLXDProvider(already_installed=is_installed)

                self.assertIs(is_installed, provider.is_provider_available())

    def test_get_instance_name(self):
        provider = makeLXDProvider()

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
        provider = makeLXDProvider()

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
        provider = makeLXDProvider()

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
        provider = makeLXDProvider()

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
        mock_lxc.profile_show.return_value = {
            "config": {"sentinel": "true"},
            "devices": {"eth0": {}},
        }
        mock_lxc.project_list.return_value = []
        mock_lxc.remote_list.return_value = {}
        mock_launcher = Mock(spec=launch)
        provider = makeLXDProvider(lxc=mock_lxc, lxd_launcher=mock_launcher)

        with provider.launched_environment(
            project_name="my-project",
            project_path=self.mock_path,
            series="focal",
            architecture="amd64",
        ) as instance:
            self.assertIsNotNone(instance)
            mock_lxc.remote_add.assert_called_once()
            mock_lxc.project_list.assert_called_once_with("test-remote")
            mock_lxc.project_create.assert_called_once_with(
                project="test-project", remote="test-remote"
            )
            mock_lxc.profile_show.assert_called_once_with(
                profile="default", project="default", remote="test-remote"
            )
            mock_lxc.profile_edit.assert_called_once_with(
                profile="default",
                config={
                    "config": {"sentinel": "true"},
                    "devices": {"eth0": {}},
                },
                project="test-project",
                remote="test-remote",
            )
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
                        use_base_instance=True,
                        project="test-project",
                        remote="test-remote",
                        lxc=mock_lxc,
                    ),
                    call().mount(
                        host_source=self.mock_path,
                        target=Path("/root/tmp-project"),
                    ),
                    call().lxc.exec(
                        instance_name=expected_instance_name,
                        command=["rm", "-rf", "/build/lpcraft/project"],
                        project="test-project",
                        remote="test-remote",
                        runner=subprocess.run,
                        check=True,
                    ),
                    call().lxc.exec(
                        instance_name=expected_instance_name,
                        command=["mkdir", "-p", "/build/lpcraft"],
                        project="test-project",
                        remote="test-remote",
                        runner=subprocess.run,
                        check=True,
                    ),
                    call().lxc.exec(
                        instance_name=expected_instance_name,
                        command=[
                            "cp",
                            "-a",
                            "/root/tmp-project",
                            "/build/lpcraft/project",
                        ],
                        project="test-project",
                        remote="test-remote",
                        runner=subprocess.run,
                        check=True,
                    ),
                    call().unmount(target=Path("/root/tmp-project")),
                ],
                mock_launcher.mock_calls,
            )
            mock_launcher.reset_mock()

        self.assertEqual(
            [
                call().lxc.exec(
                    instance_name=expected_instance_name,
                    command=["rm", "-rf", "/build/lpcraft/project"],
                    project="test-project",
                    remote="test-remote",
                    runner=subprocess.run,
                    check=True,
                ),
                call().unmount_all(),
                call().stop(),
            ],
            mock_launcher.mock_calls,
        )

    def test_launched_environment_launch_base_configuration_error(self):
        error = BaseConfigurationError(brief="Boom")
        mock_launcher = Mock(
            "craft_providers.lxd.launch", autospec=True, side_effect=error
        )
        provider = makeLXDProvider(lxd_launcher=mock_launcher)

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
        provider = makeLXDProvider(lxd_launcher=mock_launcher)
        with self.assertRaisesRegex(CommandError, r"Boom") as raised:
            with provider.launched_environment(
                project_name="my-project",
                project_path=self.mock_path,
                series="focal",
                architecture="amd64",
            ):
                pass  # pragma: no cover

        self.assertIs(error, raised.exception.__cause__)

    def test_launched_environment_unmounts_and_stops_after_copy_error(self):
        def execute(
            command: List[str], **kwargs: Any
        ) -> "subprocess.CompletedProcess[AnyStr]":
            if command[0] == "cp":
                raise subprocess.CalledProcessError(1, command)
            else:
                return subprocess.CompletedProcess([], 0)

        expected_instance_name = "lpcraft-my-project-12345-focal-amd64"
        mock_launcher = Mock(spec=launch)
        provider = makeLXDProvider(lxd_launcher=mock_launcher)
        mock_launcher.return_value.lxc.exec.side_effect = execute
        with self.assertRaisesRegex(
            CommandError, r"returned non-zero exit status 1"
        ):
            with provider.launched_environment(
                project_name="my-project",
                project_path=self.mock_path,
                series="focal",
                architecture="amd64",
            ):
                pass  # pragma: no cover

        self.assertEqual(
            [
                ANY,
                call().mount(
                    host_source=self.mock_path,
                    target=Path("/root/tmp-project"),
                ),
                call().lxc.exec(
                    instance_name=expected_instance_name,
                    command=["rm", "-rf", "/build/lpcraft/project"],
                    project="test-project",
                    remote="test-remote",
                    runner=subprocess.run,
                    check=True,
                ),
                call().lxc.exec(
                    instance_name=expected_instance_name,
                    command=["mkdir", "-p", "/build/lpcraft"],
                    project="test-project",
                    remote="test-remote",
                    runner=subprocess.run,
                    check=True,
                ),
                call().lxc.exec(
                    instance_name=expected_instance_name,
                    command=[
                        "cp",
                        "-a",
                        "/root/tmp-project",
                        "/build/lpcraft/project",
                    ],
                    project="test-project",
                    remote="test-remote",
                    runner=subprocess.run,
                    check=True,
                ),
                call().unmount(target=Path("/root/tmp-project")),
                call().lxc.exec(
                    instance_name=expected_instance_name,
                    command=["rm", "-rf", "/build/lpcraft/project"],
                    project="test-project",
                    remote="test-remote",
                    runner=subprocess.run,
                    check=True,
                ),
                call().unmount_all(),
                call().stop(),
            ],
            mock_launcher.mock_calls,
        )

    def test_launched_environment_unmounts_and_stops_after_error(self):
        expected_instance_name = "lpcraft-my-project-12345-focal-amd64"
        mock_launcher = Mock(spec=launch)
        provider = makeLXDProvider(lxd_launcher=mock_launcher)
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
            [
                call().lxc.exec(
                    instance_name=expected_instance_name,
                    command=["rm", "-rf", "/build/lpcraft/project"],
                    project="test-project",
                    remote="test-remote",
                    runner=subprocess.run,
                    check=True,
                ),
                call().unmount_all(),
                call().stop(),
            ],
            mock_launcher.mock_calls,
        )

    def test_launched_environment_unmount_all_error(self):
        error = LXDError(brief="Boom")
        mock_launcher = Mock(spec=launch)
        mock_launcher.return_value.unmount_all.side_effect = error
        provider = makeLXDProvider(lxd_launcher=mock_launcher)

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
        provider = makeLXDProvider(lxd_launcher=mock_launcher)

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
        provider = makeLXDProvider()

        with self.assertRaisesRegex(CommandError, r"Boom") as raised:
            with provider.launched_environment(
                project_name="my-project",
                project_path=self.mock_path,
                series="focal",
                architecture="amd64",
            ):
                pass  # pragma: no cover

        self.assertIs(error, raised.exception.__cause__)

    def test_launched_environment_reuses_existing_profile(self):
        mock_lxc = Mock(spec=LXC)
        mock_lxc.profile_show.return_value = {"config": {}, "devices": {}}
        mock_lxc.project_list.return_value = ["test-project"]
        mock_lxc.remote_list.return_value = {"test-remote": {}}
        mock_launcher = Mock(spec=launch)
        provider = makeLXDProvider(lxc=mock_lxc, lxd_launcher=mock_launcher)

        with provider.launched_environment(
            project_name="my-project",
            project_path=self.mock_path,
            series="focal",
            architecture="amd64",
        ) as instance:
            self.assertIsNotNone(instance)
            mock_lxc.project_create.assert_not_called()

    def test_launched_environment_removes_gpu_nvidia_configuration(self):
        # With gpu_nvidia=False, launched_environment removes any existing
        # NVIDIA GPU configuration from the default profile.
        mock_lxc = Mock(spec=LXC)
        mock_lxc.profile_show.return_value = {
            "config": {"nvidia.runtime": "true"},
            "devices": {"gpu": {"type": "gpu"}},
        }
        mock_lxc.project_list.return_value = []
        mock_lxc.remote_list.return_value = {}
        mock_launcher = Mock(spec=launch)
        provider = makeLXDProvider(lxc=mock_lxc, lxd_launcher=mock_launcher)

        with provider.launched_environment(
            project_name="my-project",
            project_path=self.mock_path,
            series="focal",
            architecture="amd64",
        ) as instance:
            self.assertIsNotNone(instance)
            mock_lxc.profile_edit.assert_called_once_with(
                profile="default",
                config={"config": {}, "devices": {}},
                project="test-project",
                remote="test-remote",
            )

    def test_launched_environment_adds_gpu_nvidia_configuration(self):
        # With gpu_nvidia=True, launched_environment adds NVIDIA GPU
        # configuration to the default profile.
        mock_lxc = Mock(spec=LXC)
        mock_lxc.profile_show.return_value = {"config": {}, "devices": {}}
        mock_lxc.project_list.return_value = []
        mock_lxc.remote_list.return_value = {}
        mock_launcher = Mock(spec=launch)
        provider = makeLXDProvider(lxc=mock_lxc, lxd_launcher=mock_launcher)

        with provider.launched_environment(
            project_name="my-project",
            project_path=self.mock_path,
            series="focal",
            architecture="amd64",
            gpu_nvidia=True,
        ) as instance:
            self.assertIsNotNone(instance)
            mock_lxc.profile_edit.assert_called_once_with(
                profile="default",
                config={
                    "config": {"nvidia.runtime": "true"},
                    "devices": {"gpu": {"type": "gpu"}},
                },
                project="test-project",
                remote="test-remote",
            )
