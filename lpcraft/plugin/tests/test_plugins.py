# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

import subprocess
from pathlib import Path, PosixPath
from textwrap import dedent
from unittest.mock import ANY, Mock, call, patch

from craft_providers.lxd import LXC, launch

from lpcraft.commands.tests import CommandBaseTestCase
from lpcraft.errors import CommandError, YAMLError
from lpcraft.providers._lxd import LXDProvider, _LXDLauncher
from lpcraft.providers.tests import FakeLXDInstaller


class TestPlugins(CommandBaseTestCase):
    def makeLXDProvider(
        self,
        is_ready=True,
        lxd_launcher=_LXDLauncher,
    ):
        lxc = Mock(spec=LXC)
        lxc.remote_list.return_value = {}
        lxd_installer = FakeLXDInstaller(is_ready=is_ready)
        return LXDProvider(
            lxc=lxc,
            lxd_installer=lxd_installer,
            lxd_launcher=lxd_launcher,
        )

    @patch("lpcraft.commands.run.get_provider")
    @patch("lpcraft.commands.run.get_host_architecture", return_value="amd64")
    def test_builtin_plugin(
        self, mock_get_host_architecture, mock_get_provider
    ):
        launcher = Mock(spec=launch)
        provider = self.makeLXDProvider(lxd_launcher=launcher)
        mock_get_provider.return_value = provider
        execute_run = launcher.return_value.execute_run
        execute_run.return_value = subprocess.CompletedProcess([], 0)
        config = dedent(
            """
            pipeline:
                - test

            jobs:
                test:
                    series: focal
                    architectures: amd64
                    packages: [nginx, apache2]
                    plugin: tox
            """
        )
        Path(".launchpad.yaml").write_text(config)

        self.run_command("run")

        self.assertEqual(
            [
                call(
                    ["apt", "install", "-y", "tox", "nginx", "apache2"],
                    cwd=PosixPath("/root/project"),
                    env=None,
                    stdout=ANY,
                    stderr=ANY,
                ),
                call(
                    ["bash", "--noprofile", "--norc", "-ec", "tox"],
                    cwd=PosixPath("/root/project"),
                    env=None,
                    stdout=ANY,
                    stderr=ANY,
                ),
            ],
            execute_run.call_args_list,
        )

    @patch("lpcraft.commands.run.get_provider")
    @patch("lpcraft.commands.run.get_host_architecture", return_value="amd64")
    def test_execute_unknown_plugin(
        self, mock_get_host_architecture, mock_get_provider
    ):
        launcher = Mock(spec=launch)
        provider = self.makeLXDProvider(lxd_launcher=launcher)
        mock_get_provider.return_value = provider
        execute_run = launcher.return_value.execute_run
        execute_run.return_value = subprocess.CompletedProcess([], 0)
        config = dedent(
            """
            pipeline:
                - test

            jobs:
                test:
                    series: focal
                    architectures: amd64
                    packages: [nginx, apache2]
                    run: non-existing
                    plugin: non-existing
            """
        )
        Path(".launchpad.yaml").write_text(config)

        result = self.run_command("run")

        self.assertEqual(1, result.exit_code)
        self.assertEqual([YAMLError("Unknown plugin")], result.errors)

    @patch("lpcraft.commands.run.get_provider")
    @patch("lpcraft.commands.run.get_host_architecture", return_value="amd64")
    def test_defining_two_run_commands_errors(
        self, mock_get_host_architecture, mock_get_provider
    ):
        # defining a run command both in the configuration file and
        # in a plugin results in an error
        launcher = Mock(spec=launch)
        provider = self.makeLXDProvider(lxd_launcher=launcher)
        mock_get_provider.return_value = provider
        execute_run = launcher.return_value.execute_run
        execute_run.return_value = subprocess.CompletedProcess([], 0)
        config = dedent(
            """
            pipeline:
                - test

            jobs:
                test:
                    series: focal
                    architectures: amd64
                    packages: [nginx, apache2]
                    run: tox
                    plugin: tox
            """
        )
        Path(".launchpad.yaml").write_text(config)

        result = self.run_command("run")

        self.assertEqual(1, result.exit_code)
        self.assertEqual(
            result.errors,
            [
                CommandError(
                    "Job 'test' for focal/amd64 sets more than one 'run' "
                    "command. Maybe you have set a run command both in the "
                    "configuration and in a plugin?"
                )
            ],
        )
