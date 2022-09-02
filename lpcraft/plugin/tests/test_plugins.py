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
from pydantic import StrictStr, ValidationError, validator

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
                    cwd=PosixPath("/build/lpcraft/project"),
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
                    cwd=PosixPath("/build/lpcraft/project"),
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
                    cwd=PosixPath("/build/lpcraft/project"),
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
                    cwd=PosixPath("/build/lpcraft/project"),
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
                    cwd=PosixPath("/build/lpcraft/project"),
                    env={"TOX_TESTENV_PASSENV": "http_proxy https_proxy"},
                    stdout=ANY,
                    stderr=ANY,
                ),
                call(
                    ["bash", "--noprofile", "--norc", "-ec", "ls"],
                    cwd=PosixPath("/build/lpcraft/project"),
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
                    cwd=PosixPath("/build/lpcraft/project"),
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
                    cwd=PosixPath("/build/lpcraft/project"),
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
                    cwd=PosixPath("/build/lpcraft/project"),
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

    @patch("lpcraft.commands.run.get_provider")
    @patch("lpcraft.commands.run.get_host_architecture", return_value="amd64")
    def test_miniconda_plugin(
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
                    plugin: miniconda
                    conda-channels:
                        - conda-forge
                    conda-packages:
                        - mamba
                        - pip
                    conda-python: 3.8
                    run: |
                        pip install --upgrade pytest
            """
        )
        Path(".launchpad.yaml").write_text(config)
        pre_run_command = dedent(
            """
        if [ ! -d "$HOME/miniconda3" ]; then
            wget -O /tmp/miniconda.sh https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh
            chmod +x /tmp/miniconda.sh
            /tmp/miniconda.sh -b
        fi
        export PATH=$HOME/miniconda3/bin:$PATH
        conda remove --all -q -y -n $CONDA_ENV
        conda create -n $CONDA_ENV -q -y -c conda-forge -c defaults PYTHON=3.8 mamba pip
        source activate $CONDA_ENV
        """  # noqa:E501
        )

        run_command = dedent(
            """
            export PATH=$HOME/miniconda3/bin:$PATH
            source activate $CONDA_ENV
            pip install --upgrade pytest
        """
        )
        post_run_command = (
            "export PATH=$HOME/miniconda3/bin:$PATH; "
            "source activate $CONDA_ENV; conda env export"
        )

        self.run_command("run")

        self.assertEqual(
            [
                call(
                    ["apt", "update"],
                    cwd=PosixPath("/build/lpcraft/project"),
                    env={"CONDA_ENV": "lpci"},
                    stdout=ANY,
                    stderr=ANY,
                ),
                call(
                    [
                        "apt",
                        "install",
                        "-y",
                        "git",
                        "python3-dev",
                        "python3-pip",
                        "python3-venv",
                        "wget",
                    ],
                    cwd=PosixPath("/build/lpcraft/project"),
                    env={"CONDA_ENV": "lpci"},
                    stdout=ANY,
                    stderr=ANY,
                ),
                call(
                    [
                        "bash",
                        "--noprofile",
                        "--norc",
                        "-ec",
                        pre_run_command,
                    ],
                    cwd=PosixPath("/build/lpcraft/project"),
                    env={"CONDA_ENV": "lpci"},
                    stdout=ANY,
                    stderr=ANY,
                ),
                call(
                    [
                        "bash",
                        "--noprofile",
                        "--norc",
                        "-ec",
                        run_command,
                    ],
                    cwd=PosixPath("/build/lpcraft/project"),
                    env={"CONDA_ENV": "lpci"},
                    stdout=ANY,
                    stderr=ANY,
                ),
                call(
                    [
                        "bash",
                        "--noprofile",
                        "--norc",
                        "-ec",
                        post_run_command,
                    ],
                    cwd=PosixPath("/build/lpcraft/project"),
                    env={"CONDA_ENV": "lpci"},
                    stdout=ANY,
                    stderr=ANY,
                ),
            ],
            execute_run.call_args_list,
        )

    def test_miniconda_plugin_works_without_plugin_settings(self):
        config = dedent(
            """
            pipeline:
                - build

            jobs:
                build:
                    series: focal
                    architectures: amd64
                    plugin: miniconda
                    run: |
                        pip install --upgrade pytest
        """
        )
        config_path = Path(".launchpad.yaml")
        config_path.write_text(config)
        config_obj = lpcraft.config.Config.load(config_path)
        self.assertEqual(config_obj.jobs["build"][0].plugin, "miniconda")
        pm = get_plugin_manager(config_obj.jobs["build"][0])
        plugins = pm.get_plugins()
        plugin_match = [
            _ for _ in plugins if _.__class__.__name__ == "MiniCondaPlugin"
        ]
        self.assertEqual(
            [
                "defaults",
            ],
            plugin_match[0].conda_channels,
        )
        self.assertEqual(["PYTHON=3.8", "pip"], plugin_match[0].conda_packages)

    @patch("lpcraft.commands.run.get_provider")
    @patch("lpcraft.commands.run.get_host_architecture", return_value="amd64")
    def test_conda_build_plugin(
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
                    plugin: conda-build
                    build-target: info/recipe/parent
                    conda-channels:
                        - conda-forge
                    conda-packages:
                        - mamba
                        - pip
                    conda-python: 3.8
                    run: |
                        pip install --upgrade pytest
            """
        )
        Path(".launchpad.yaml").write_text(config)
        Path("info/recipe/parent").mkdir(parents=True)
        Path("info/recipe/meta.yaml").touch()
        Path("info/recipe/parent/meta.yaml").touch()
        pre_run_command = dedent(
            """
        if [ ! -d "$HOME/miniconda3" ]; then
            wget -O /tmp/miniconda.sh https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh
            chmod +x /tmp/miniconda.sh
            /tmp/miniconda.sh -b
        fi
        export PATH=$HOME/miniconda3/bin:$PATH
        conda remove --all -q -y -n $CONDA_ENV
        conda create -n $CONDA_ENV -q -y -c conda-forge -c defaults -c https://user:pass@canonical.example.com/artifactory/soss-conda-stable-local/ PYTHON=3.8 conda-build mamba pip
        source activate $CONDA_ENV
        """  # noqa:E501
        )
        run_command = dedent(
            """
            export PATH=$HOME/miniconda3/bin:$PATH
            source activate $CONDA_ENV
            conda-build --no-anaconda-upload --output-folder dist -c conda-forge -c defaults -c https://user:pass@canonical.example.com/artifactory/soss-conda-stable-local/ info/recipe/parent
            pip install --upgrade pytest
        """  # noqa: E501
        )
        post_run_command = (
            "export PATH=$HOME/miniconda3/bin:$PATH; "
            "source activate $CONDA_ENV; conda env export"
        )

        self.run_command(
            "run",
            "--plugin-setting",
            "miniconda_conda_channel=https://user:pass@canonical.example.com/artifactory/soss-conda-stable-local/",  # noqa: E501
        )

        self.assertEqual(
            call(
                ["apt", "update"],
                cwd=PosixPath("/build/lpcraft/project"),
                env={"CONDA_ENV": "lpci"},
                stdout=ANY,
                stderr=ANY,
            ),
            execute_run.call_args_list[0],
        )
        self.assertEqual(
            call(
                [
                    "apt",
                    "install",
                    "-y",
                    "git",
                    "python3-dev",
                    "python3-pip",
                    "python3-venv",
                    "wget",
                    "automake",
                    "build-essential",
                    "cmake",
                    "gcc",
                    "g++",
                    "libc++-dev",
                    "libc6-dev",
                    "libffi-dev",
                    "libjpeg-dev",
                    "libpng-dev",
                    "libreadline-dev",
                    "libsqlite3-dev",
                    "libtool",
                    "zlib1g-dev",
                ],
                cwd=PosixPath("/build/lpcraft/project"),
                env={"CONDA_ENV": "lpci"},
                stdout=ANY,
                stderr=ANY,
            ),
            execute_run.call_args_list[1],
        )
        self.assertEqual(
            call(
                [
                    "bash",
                    "--noprofile",
                    "--norc",
                    "-ec",
                    pre_run_command,
                ],
                cwd=PosixPath("/build/lpcraft/project"),
                env={"CONDA_ENV": "lpci"},
                stdout=ANY,
                stderr=ANY,
            ),
            execute_run.call_args_list[2],
        )
        self.assertEqual(
            call(
                [
                    "bash",
                    "--noprofile",
                    "--norc",
                    "-ec",
                    run_command,
                ],
                cwd=PosixPath("/build/lpcraft/project"),
                env={"CONDA_ENV": "lpci"},
                stdout=ANY,
                stderr=ANY,
            ),
            execute_run.call_args_list[3],
        )
        self.assertEqual(
            call(
                [
                    "bash",
                    "--noprofile",
                    "--norc",
                    "-ec",
                    post_run_command,
                ],
                cwd=PosixPath("/build/lpcraft/project"),
                env={"CONDA_ENV": "lpci"},
                stdout=ANY,
                stderr=ANY,
            ),
            execute_run.call_args_list[4],
        )

    def test_conda_build_plugin_finds_recipe(self):
        config = dedent(
            """
            pipeline:
                - build

            jobs:
                build:
                    series: focal
                    architectures: amd64
                    plugin: conda-build
                    conda-channels:
                        - conda-forge
                    conda-packages:
                        - mamba
                        - pip
                    conda-python: 3.8
                    run: |
                        pip install --upgrade pytest
        """
        )
        config_path = Path(".launchpad.yaml")
        config_path.write_text(config)
        Path("include/fake_subdir").mkdir(parents=True)
        meta_yaml = Path("info/recipe/meta.yaml")
        meta_yaml.parent.mkdir(parents=True)
        meta_yaml.touch()
        config_obj = lpcraft.config.Config.load(config_path)
        self.assertEqual(config_obj.jobs["build"][0].plugin, "conda-build")
        pm = get_plugin_manager(config_obj.jobs["build"][0])
        plugins = pm.get_plugins()
        plugin_match = [
            _ for _ in plugins if _.__class__.__name__ == "CondaBuildPlugin"
        ]
        self.assertEqual("info/recipe", plugin_match[0].build_target)

    def test_conda_build_plugin_finds_recipe_with_fake_parent(self):
        config = dedent(
            """
            pipeline:
                - build

            jobs:
                build:
                    series: focal
                    architectures: amd64
                    plugin: conda-build
                    conda-channels:
                        - conda-forge
                    conda-packages:
                        - mamba
                        - pip
                    conda-python: 3.8
                    run: |
                        pip install --upgrade pytest
        """
        )
        config_path = Path(".launchpad.yaml")
        config_path.write_text(config)
        meta_yaml = Path("info/recipe/meta.yaml")
        meta_yaml.parent.mkdir(parents=True)
        parent_path = meta_yaml.parent.joinpath("parent")
        parent_path.mkdir()
        parent_path.joinpath("some_file.yaml").touch()
        meta_yaml.touch()
        config_obj = lpcraft.config.Config.load(config_path)
        self.assertEqual(config_obj.jobs["build"][0].plugin, "conda-build")
        pm = get_plugin_manager(config_obj.jobs["build"][0])
        plugins = pm.get_plugins()
        plugin_match = [
            _ for _ in plugins if _.__class__.__name__ == "CondaBuildPlugin"
        ]
        self.assertEqual("info/recipe", plugin_match[0].build_target)

    def test_conda_build_plugin_finds_parent_recipe(self):
        config = dedent(
            """
            pipeline:
                - build

            jobs:
                build:
                    series: focal
                    architectures: amd64
                    plugin: conda-build
                    conda-channels:
                        - conda-forge
                    conda-packages:
                        - mamba
                        - pip
                    conda-python: 3.8
                    run: |
                        pip install --upgrade pytest
        """
        )
        config_path = Path(".launchpad.yaml")
        config_path.write_text(config)
        Path("include/fake_subdir").mkdir(parents=True)
        meta_yaml = Path("info/recipe/meta.yaml")
        parent_meta_yaml = meta_yaml.parent.joinpath("parent/meta.yaml")
        parent_meta_yaml.parent.mkdir(parents=True)
        meta_yaml.touch()
        parent_meta_yaml.touch()
        config_obj = lpcraft.config.Config.load(config_path)
        self.assertEqual(config_obj.jobs["build"][0].plugin, "conda-build")
        pm = get_plugin_manager(config_obj.jobs["build"][0])
        plugins = pm.get_plugins()
        plugin_match = [
            _ for _ in plugins if _.__class__.__name__ == "CondaBuildPlugin"
        ]
        self.assertEqual("info/recipe/parent", plugin_match[0].build_target)

    def test_conda_build_plugin_uses_child_vars_with_parent_recipe(self):
        config = dedent(
            """
            pipeline:
                - build

            jobs:
                build:
                    series: focal
                    architectures: amd64
                    plugin: conda-build
                    conda-channels:
                        - conda-forge
                    conda-packages:
                        - mamba
                        - pip
                    conda-python: 3.8
                    run: |
                        pip install --upgrade pytest
        """
        )
        run_command = dedent(
            """
            export PATH=$HOME/miniconda3/bin:$PATH
            source activate $CONDA_ENV
            conda-build --no-anaconda-upload --output-folder dist -c conda-forge -c defaults -m info/recipe/parent/conda_build_config.yaml -m info/recipe/conda_build_config.yaml info/recipe/parent
            pip install --upgrade pytest
        """  # noqa: E501
        )
        config_path = Path(".launchpad.yaml")
        config_path.write_text(config)
        Path("include/fake_subdir").mkdir(parents=True)
        meta_yaml = Path("info/recipe/meta.yaml")
        variant_config = meta_yaml.with_name("conda_build_config.yaml")
        parent_meta_yaml = meta_yaml.parent.joinpath("parent/meta.yaml")
        parent_variant_config = parent_meta_yaml.with_name(
            "conda_build_config.yaml"
        )
        parent_meta_yaml.parent.mkdir(parents=True)
        meta_yaml.touch()
        variant_config.touch()
        parent_variant_config.touch()
        parent_meta_yaml.touch()
        config_obj = lpcraft.config.Config.load(config_path)
        self.assertEqual(config_obj.jobs["build"][0].plugin, "conda-build")
        pm = get_plugin_manager(config_obj.jobs["build"][0])
        plugins = pm.get_plugins()
        plugin_match = [
            _ for _ in plugins if _.__class__.__name__ == "CondaBuildPlugin"
        ]
        self.assertEqual(
            [parent_variant_config.as_posix(), variant_config.as_posix()],
            plugin_match[0].build_configs,
        )
        self.assertEqual(run_command, plugin_match[0].lpcraft_execute_run())

    def test_conda_build_plugin_renames_recipe_templates(self):
        config = dedent(
            """
            pipeline:
                - build

            jobs:
                build:
                    series: focal
                    architectures: amd64
                    plugin: conda-build
                    conda-channels:
                        - conda-forge
                    conda-packages:
                        - mamba
                        - pip
                    conda-python: 3.8
                    run: |
                        pip install --upgrade pytest
        """
        )
        config_path = Path(".launchpad.yaml")
        config_path.write_text(config)
        meta_yaml = Path("info/recipe/meta.yaml")
        template_meta_yaml = meta_yaml.with_name("meta.yaml.template")
        meta_yaml.parent.mkdir(parents=True)
        meta_yaml.touch()
        template_meta_yaml.touch()
        config_obj = lpcraft.config.Config.load(config_path)
        self.assertEqual(config_obj.jobs["build"][0].plugin, "conda-build")
        pm = get_plugin_manager(config_obj.jobs["build"][0])
        plugins = pm.get_plugins()
        plugin_match = [
            _ for _ in plugins if _.__class__.__name__ == "CondaBuildPlugin"
        ]
        self.assertEqual("info/recipe", plugin_match[0].build_target)
        self.assertFalse(template_meta_yaml.is_file())

    def test_conda_build_plugin_raises_error_if_no_recipe(self):
        config = dedent(
            """
            pipeline:
                - build

            jobs:
                build:
                    series: focal
                    architectures: amd64
                    plugin: conda-build
                    conda-channels:
                        - conda-forge
                    conda-packages:
                        - mamba
                        - pip
                    conda-python: 3.8
                    run: |
                        pip install --upgrade pytest
        """
        )
        config_path = Path(".launchpad.yaml")
        config_path.write_text(config)
        config_obj = lpcraft.config.Config.load(config_path)
        self.assertRaisesRegex(
            RuntimeError,
            "No build target found",
            get_plugin_manager,
            config_obj.jobs["build"][0],
        )

    def test_conda_build_plugin_raises_error_if_no_recipe_in_recipe_folder(
        self,
    ):
        config = dedent(
            """
            pipeline:
                - build

            jobs:
                build:
                    series: focal
                    architectures: amd64
                    plugin: conda-build
                    conda-channels:
                        - conda-forge
                    conda-packages:
                        - mamba
                        - pip
                    conda-python: 3.8
                    run: |
                        pip install --upgrade pytest
        """
        )
        config_path = Path(".launchpad.yaml")
        config_path.write_text(config)
        Path("include/fake_subdir").mkdir(parents=True)
        # there is a recipe folder, but no meta.yaml file
        meta_yaml = Path("info/recipe/")
        meta_yaml.mkdir(parents=True)
        config_obj = lpcraft.config.Config.load(config_path)
        self.assertRaisesRegex(
            RuntimeError,
            "No build target found",
            get_plugin_manager,
            config_obj.jobs["build"][0],
        )

    @patch("lpcraft.commands.run.get_provider")
    @patch("lpcraft.commands.run.get_host_architecture", return_value="amd64")
    def test_additional_settings(
        self, mock_get_host_architecture, mock_get_provider
    ):
        # XXX jugmac00 2022-06-13
        # this test covers the case when there are additional plugin settings,
        # but not soss related
        # this has not (yet) a real use case, but is necessary for coverage
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
                    plugin: conda-build
                    build-target: info/recipe/parent
                    conda-channels:
                        - conda-forge
                    conda-packages:
                        - mamba
                        - pip
                    conda-python: 3.8
                    run: |
                        pip install --upgrade pytest
            """
        )
        Path(".launchpad.yaml").write_text(config)

        result = self.run_command(
            "run",
            "--plugin-setting",
            "foo=bar",
        )

        self.assertEqual(0, result.exit_code)

    @patch("lpcraft.commands.run.get_provider")
    @patch("lpcraft.commands.run.get_host_architecture", return_value="amd64")
    def test_golang_plugin(
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
                    plugin: golang
                    golang-version: "1.17"
                    series: focal
                    architectures: amd64
                    packages: [file, git]
                    run: go build -x examples/go-top.go
            """
        )
        Path(".launchpad.yaml").write_text(config)

        self.run_command("run")
        self.assertEqual(
            [
                call(
                    ["apt", "update"],
                    cwd=PosixPath("/build/lpcraft/project"),
                    env={},
                    stdout=ANY,
                    stderr=ANY,
                ),
                call(
                    ["apt", "install", "-y", "golang-1.17", "file", "git"],
                    cwd=PosixPath("/build/lpcraft/project"),
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
                        "\nexport PATH=/usr/lib/go-1.17/bin/:$PATH\ngo build -x examples/go-top.go",  # noqa: E501
                    ],
                    cwd=PosixPath("/build/lpcraft/project"),
                    env={},
                    stdout=ANY,
                    stderr=ANY,
                ),
            ],
            execute_run.call_args_list,
        )

    @patch("lpcraft.commands.run.get_provider")
    @patch("lpcraft.commands.run.get_host_architecture", return_value="amd64")
    def test_golang_plugin_with_illegal_version(
        self, mock_get_host_architecture, mock_get_provider
    ):
        launcher = Mock(spec=launch)
        provider = makeLXDProvider(lxd_launcher=launcher)
        mock_get_provider.return_value = provider
        execute_run = launcher.return_value.execute_run
        execute_run.return_value = subprocess.CompletedProcess([], 0)
        # we do not allow floats as e.g. `1.20` is a problematic value in YAML
        config = dedent(
            """
            pipeline:
                - build
            jobs:
                build:
                    plugin: golang
                    golang-version: 1.18
                    series: focal
                    architectures: amd64
                    packages: [file, git]
                    run: go build -x examples/go-top.go
            """
        )
        Path(".launchpad.yaml").write_text(config)

        result = self.run_command("run")

        self.assertEqual(1, result.exit_code)

        [error] = result.errors
        self.assertIn("str type expected", str(error))

    def test_load_golang_plugin_configuration_with_invalid_version(self):
        config = dedent(
            """
            pipeline:
                - build
            jobs:
                build:
                    plugin: golang
                    golang-version: 1.18
                    series: focal
                    architectures: amd64
                    packages: [file, git]
                    run: go build -x examples/go-top.go
            """
        )
        config_path = Path(".launchpad.yaml")
        config_path.write_text(config)

        self.assertRaises(
            ValidationError,
            lpcraft.config.Config.load,
            config_path,
        )
