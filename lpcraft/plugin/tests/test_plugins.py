# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

import os
import subprocess
from pathlib import Path, PosixPath
from textwrap import dedent
from unittest.mock import ANY, Mock, call, patch

from craft_providers.lxd import launch
from fixtures import TempDir

from lpcraft.commands.tests import CommandBaseTestCase
from lpcraft.errors import ConfigurationError
from lpcraft.providers.tests import makeLXDProvider


class TestPlugins(CommandBaseTestCase):
    def setUp(self):
        super().setUp()
        tempdir = Path(self.useFixture(TempDir()).path)
        cwd = Path.cwd()
        os.chdir(tempdir)
        self.addCleanup(os.chdir, cwd)

    @patch("lpcraft.commands.run.get_provider")
    @patch("lpcraft.commands.run.get_host_architecture", return_value="amd64")
    def test_tox_plugin(self, mock_get_host_architecture, mock_get_provider):
        launcher = Mock(spec=launch)
        provider = makeLXDProvider(lxd_launcher=launcher)
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
                    [
                        "apt",
                        "install",
                        "-y",
                        "python3-pip",
                        "nginx",
                        "apache2",
                    ],
                    cwd=PosixPath("/root/project"),
                    env={"PLUGIN": "tox"},
                    stdout=ANY,
                    stderr=ANY,
                ),
                call(
                    [
                        "bash",
                        "--noprofile",
                        "--norc",
                        "-ec",
                        "python3 -m pip install tox==3.24.5; tox",
                    ],
                    cwd=PosixPath("/root/project"),
                    env={"PLUGIN": "tox"},
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
        provider = makeLXDProvider(lxd_launcher=launcher)
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
        self.assertEqual([ConfigurationError("Unknown plugin")], result.errors)

    @patch("lpcraft.commands.run.get_provider")
    @patch("lpcraft.commands.run.get_host_architecture", return_value="amd64")
    def test_run_command_from_configuration_takes_precedence(
        self, mock_get_host_architecture, mock_get_provider
    ):
        launcher = Mock(spec=launch)
        provider = makeLXDProvider(lxd_launcher=launcher)
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
                    run: ls
                    plugin: tox
            """
        )
        Path(".launchpad.yaml").write_text(config)

        self.run_command("run")

        self.assertEqual(
            [
                call(
                    [
                        "apt",
                        "install",
                        "-y",
                        "python3-pip",
                        "nginx",
                        "apache2",
                    ],
                    cwd=PosixPath("/root/project"),
                    env={"PLUGIN": "tox"},
                    stdout=ANY,
                    stderr=ANY,
                ),
                call(
                    ["bash", "--noprofile", "--norc", "-ec", "ls"],
                    cwd=PosixPath("/root/project"),
                    env={"PLUGIN": "tox"},
                    stdout=ANY,
                    stderr=ANY,
                ),
            ],
            execute_run.call_args_list,
        )

    @patch("lpcraft.commands.run.get_provider")
    @patch("lpcraft.commands.run.get_host_architecture", return_value="amd64")
    def test_pyproject_build_plugin(
        self, mock_get_host_architecture, mock_get_provider
    ):
        launcher = Mock(spec=launch)
        provider = makeLXDProvider(lxd_launcher=launcher)
        mock_get_provider.return_value = provider
        execute_run = launcher.return_value.execute_run
        execute_run.return_value = subprocess.CompletedProcess([], 0)
        config = dedent(
            """
            pipeline:
                - build

            jobs:
                build:
                    series: focal
                    architectures: amd64
                    plugin: pyproject-build
            """
        )
        Path(".launchpad.yaml").write_text(config)

        self.run_command("run")

        self.assertEqual(
            [
                call(
                    [
                        "apt",
                        "install",
                        "-y",
                        "python3-pip",
                        "python3-venv",
                    ],
                    cwd=PosixPath("/root/project"),
                    env={},
                    stdout=ANY,
                    stderr=ANY,
                ),
                call(
                    [
                        "bash",
                        "--noprofile",
                        "--norc",
                        "-ec",
                        "python3 -m pip install build==0.7.0; python3 -m build",  # noqa: E501
                    ],
                    cwd=PosixPath("/root/project"),
                    env={},
                    stdout=ANY,
                    stderr=ANY,
                ),
            ],
            execute_run.call_args_list,
        )
