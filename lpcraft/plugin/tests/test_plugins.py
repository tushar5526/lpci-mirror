# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

import os
import subprocess
from pathlib import Path, PosixPath
from textwrap import dedent
from typing import List, Optional, Union, cast
from unittest.mock import ANY, Mock, call, patch

from craft_providers.lxd import launch
from fixtures import TempDir
from pydantic import StrictStr, validator

import lpcraft.config
from lpcraft.commands.tests import CommandBaseTestCase
from lpcraft.errors import ConfigurationError
from lpcraft.plugin.manager import get_plugin_manager
from lpcraft.plugins import register
from lpcraft.plugins.plugins import BaseConfig, BasePlugin
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
                    ["apt", "update"],
                    cwd=PosixPath("/root/lpcraft/project"),
                    env={"TOX_TESTENV_PASSENV": "http_proxy https_proxy"},
                    stdout=ANY,
                    stderr=ANY,
                ),
                call(
                    [
                        "apt",
                        "install",
                        "-y",
                        "python3-pip",
                        "nginx",
                        "apache2",
                    ],
                    cwd=PosixPath("/root/lpcraft/project"),
                    env={"TOX_TESTENV_PASSENV": "http_proxy https_proxy"},
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
                    cwd=PosixPath("/root/lpcraft/project"),
                    env={"TOX_TESTENV_PASSENV": "http_proxy https_proxy"},
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
                    ["apt", "update"],
                    cwd=PosixPath("/root/lpcraft/project"),
                    env={"TOX_TESTENV_PASSENV": "http_proxy https_proxy"},
                    stdout=ANY,
                    stderr=ANY,
                ),
                call(
                    [
                        "apt",
                        "install",
                        "-y",
                        "python3-pip",
                        "nginx",
                        "apache2",
                    ],
                    cwd=PosixPath("/root/lpcraft/project"),
                    env={"TOX_TESTENV_PASSENV": "http_proxy https_proxy"},
                    stdout=ANY,
                    stderr=ANY,
                ),
                call(
                    ["bash", "--noprofile", "--norc", "-ec", "ls"],
                    cwd=PosixPath("/root/lpcraft/project"),
                    env={"TOX_TESTENV_PASSENV": "http_proxy https_proxy"},
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
                    ["apt", "update"],
                    cwd=PosixPath("/root/lpcraft/project"),
                    env={},
                    stdout=ANY,
                    stderr=ANY,
                ),
                call(
                    [
                        "apt",
                        "install",
                        "-y",
                        "python3-pip",
                        "python3-venv",
                    ],
                    cwd=PosixPath("/root/lpcraft/project"),
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
                    cwd=PosixPath("/root/lpcraft/project"),
                    env={},
                    stdout=ANY,
                    stderr=ANY,
                ),
            ],
            execute_run.call_args_list,
        )

    def test_plugin_config_raises_notimplementederror(self):
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
        config_path = Path(".launchpad.yaml")
        config_path.write_text(config)
        config_obj = lpcraft.config.Config.load(config_path)
        self.assertEqual(config_obj.jobs["build"][0].plugin, "pyproject-build")
        pm = get_plugin_manager(config_obj.jobs["build"][0])
        plugins = pm.get_plugins()
        build_plugin = [
            _
            for _ in plugins
            if _.__class__.__name__ == "PyProjectBuildPlugin"
        ]
        # build_plugin does not define its own configuration
        self.assertRaises(
            NotImplementedError, build_plugin[0].get_plugin_config
        )

    def test_plugin_config_sets_values(self):
        config = dedent(
            """
            pipeline:
                - build

            jobs:
                build:
                    series: focal
                    architectures: amd64
                    plugin: fake-plugin
                    python-version: 3.8
        """
        )
        config_path = Path(".launchpad.yaml")
        config_path.write_text(config)

        @register(name="fake-plugin")
        class FakePlugin(BasePlugin):
            class Config(BaseConfig):
                series: Optional[List[StrictStr]]
                python_version: Optional[StrictStr]

                @validator("python_version", pre=True)
                def validate_python_version(
                    cls, v: Union[str, float, int]
                ) -> str:
                    return str(v)

            def get_plugin_config(self) -> "FakePlugin.Config":
                return cast(FakePlugin.Config, self.config.plugin_config)

        config_obj = lpcraft.config.Config.load(config_path)
        job = config_obj.jobs["build"][0]
        pm = get_plugin_manager(job)
        plugins = pm.get_plugins()
        fake_plugin = [
            _ for _ in plugins if _.__class__.__name__ == "FakePlugin"
        ]
        self.assertEqual(job.plugin, "fake-plugin")
        plugin_config = fake_plugin[0].get_plugin_config()
        self.assertEqual(plugin_config.python_version, "3.8")
        self.assertIsNone(getattr(plugin_config, "series", None))
