# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

import os
import subprocess
from pathlib import Path, PosixPath
from textwrap import dedent
from typing import Optional
from unittest.mock import ANY, Mock, call, patch

from craft_providers.lxd import LXC, launch
from fixtures import EnvironmentVariable, TempDir
from systemfixtures import FakeProcesses
from testtools.matchers import MatchesStructure

from lpcraft.commands.tests import CommandBaseTestCase
from lpcraft.errors import CommandError, YAMLError
from lpcraft.providers._lxd import LXDProvider, _LXDLauncher
from lpcraft.providers.tests import FakeLXDInstaller


class RunJobTestCase(CommandBaseTestCase):
    def setUp(self):
        super().setUp()
        self.useFixture(EnvironmentVariable("LPCRAFT_MANAGED_MODE", "1"))
        cwd = os.getcwd()
        os.chdir(self.useFixture(TempDir()).path)
        self.addCleanup(os.chdir, cwd)

    def test_no_series(self):
        result = self.run_command("run")

        self.assertThat(
            result,
            MatchesStructure.byEquality(
                exit_code=1,
                errors=[CommandError("Series is required in managed mode")],
            ),
        )

    def test_no_job_name(self):
        result = self.run_command("run", "--series", "focal")

        self.assertThat(
            result,
            MatchesStructure.byEquality(
                exit_code=1,
                errors=[CommandError("Job name is required in managed mode")],
            ),
        )

    def test_missing_config_file(self):
        result = self.run_command("run", "--series", "focal", "test")

        self.assertThat(
            result,
            MatchesStructure.byEquality(
                exit_code=1,
                errors=[
                    YAMLError("Couldn't find config file '.launchpad.yaml'")
                ],
            ),
        )

    def test_no_matching_job(self):
        config = dedent(
            """
            pipeline:
                - test

            jobs:
                test:
                    series: focal
                    architectures: amd64
                    run: tox
            """
        )
        Path(".launchpad.yaml").write_text(config)

        result = self.run_command("run", "--series", "focal", "build")

        self.assertThat(
            result,
            MatchesStructure.byEquality(
                exit_code=1,
                errors=[CommandError("No job definition for 'build'")],
            ),
        )

    def test_no_matching_job_for_series(self):
        config = dedent(
            """
            pipeline:
                - test

            jobs:
                test:
                    series: focal
                    architectures: amd64
                    run: tox
            """
        )
        Path(".launchpad.yaml").write_text(config)

        result = self.run_command("run", "--series", "bionic", "test")

        self.assertThat(
            result,
            MatchesStructure.byEquality(
                exit_code=1,
                errors=[
                    CommandError("No job definition for 'test' for bionic")
                ],
            ),
        )

    def test_ambiguous_job_definitions(self):
        config = dedent(
            """
            pipeline:
                - test

            jobs:
                test:
                    matrix:
                        - run: make
                        - run: tox
                    series: focal
                    architectures: amd64
            """
        )
        Path(".launchpad.yaml").write_text(config)

        result = self.run_command("run", "--series", "focal", "test")

        self.assertThat(
            result,
            MatchesStructure.byEquality(
                exit_code=1,
                errors=[
                    CommandError(
                        "Ambiguous job definitions for 'test' for focal"
                    )
                ],
            ),
        )

    def test_no_run_definition(self):
        config = dedent(
            """
            pipeline:
                - test

            jobs:
                test:
                    series: focal
                    architectures: amd64
            """
        )
        Path(".launchpad.yaml").write_text(config)

        result = self.run_command("run", "--series", "focal", "test")

        self.assertThat(
            result,
            MatchesStructure.byEquality(
                exit_code=1,
                errors=[CommandError("'run' not set for job 'test'")],
            ),
        )

    def test_run_fails(self):
        processes_fixture = self.useFixture(FakeProcesses())
        processes_fixture.add(lambda _: {"returncode": 2}, name="bash")
        config = dedent(
            """
            pipeline:
                - test

            jobs:
                test:
                    series: focal
                    architectures: amd64
                    run: |
                        exit 2
            """
        )
        Path(".launchpad.yaml").write_text(config)

        result = self.run_command("run", "--series", "focal", "test")

        self.assertThat(
            result,
            MatchesStructure.byEquality(
                exit_code=2,
                errors=[
                    CommandError(
                        "Job 'test' failed with exit status 2.", retcode=2
                    )
                ],
            ),
        )
        self.assertEqual(
            [["bash", "--noprofile", "--norc", "-ec", "exit 2\n"]],
            [proc._args["args"] for proc in processes_fixture.procs],
        )

    def test_run_succeeds(self):
        processes_fixture = self.useFixture(FakeProcesses())
        processes_fixture.add(lambda _: {"returncode": 0}, name="bash")
        config = dedent(
            """
            pipeline:
                - test

            jobs:
                test:
                    series: focal
                    architectures: amd64
                    run: |
                        echo hello
                        tox
            """
        )
        Path(".launchpad.yaml").write_text(config)

        result = self.run_command("run", "--series", "focal", "test")

        self.assertEqual(0, result.exit_code)
        self.assertEqual(
            [["bash", "--noprofile", "--norc", "-ec", "echo hello\ntox\n"]],
            [proc._args["args"] for proc in processes_fixture.procs],
        )


class RunPipelineTestCase(CommandBaseTestCase):
    def setUp(self):
        super().setUp()
        self.useFixture(EnvironmentVariable("LPCRAFT_MANAGED_MODE", None))
        tmp_project_dir = self.useFixture(TempDir()).join("test-project")
        os.mkdir(tmp_project_dir)
        cwd = os.getcwd()
        os.chdir(tmp_project_dir)
        self.addCleanup(os.chdir, cwd)

    def makeLXDProvider(
        self,
        is_ready: bool = True,
        lxd_launcher: Optional[_LXDLauncher] = None,
    ) -> LXDProvider:
        lxc = Mock(spec=LXC)
        lxc.remote_list.return_value = {}
        lxd_installer = FakeLXDInstaller(is_ready=is_ready)
        if lxd_launcher is None:
            lxd_launcher = Mock(spec=launch)
        return LXDProvider(
            lxc=lxc,
            lxd_installer=lxd_installer,
            lxd_launcher=lxd_launcher,
        )

    def test_missing_config_file(self):
        result = self.run_command("run")

        self.assertThat(
            result,
            MatchesStructure.byEquality(
                exit_code=1,
                errors=[
                    YAMLError("Couldn't find config file '.launchpad.yaml'")
                ],
            ),
        )

    @patch("lpcraft.commands.run.get_provider")
    @patch("lpcraft.commands.run.get_host_architecture", return_value="amd64")
    def test_lxd_not_ready(
        self, mock_get_host_architecture, mock_get_provider
    ):
        mock_get_provider.return_value = self.makeLXDProvider(is_ready=False)
        config = dedent(
            """
            pipeline: []
            jobs: {}
            """
        )
        Path(".launchpad.yaml").write_text(config)

        result = self.run_command("run")

        self.assertThat(
            result,
            MatchesStructure.byEquality(
                exit_code=1,
                errors=[CommandError("LXD is broken")],
            ),
        )

    @patch("lpcraft.commands.run.get_provider")
    @patch("lpcraft.commands.run.get_host_architecture", return_value="amd64")
    def test_job_not_defined(
        self, mock_get_host_architecture, mock_get_provider
    ):
        mock_get_provider.return_value = self.makeLXDProvider()
        config = dedent(
            """
            pipeline:
                - test

            jobs: {}
            """
        )
        Path(".launchpad.yaml").write_text(config)

        result = self.run_command("run")

        self.assertThat(
            result,
            MatchesStructure.byEquality(
                exit_code=1,
                errors=[CommandError("No job definition for 'test'")],
            ),
        )

    @patch("lpcraft.commands.run.get_provider")
    @patch("lpcraft.commands.run.get_host_architecture", return_value="arm64")
    def test_job_not_defined_for_host_architecture(
        self, mock_get_host_architecture, mock_get_provider
    ):
        # Jobs not defined for the host architecture are skipped.  (It is
        # assumed that the dispatcher won't dispatch anything for an
        # architecture if it has no jobs at all.)
        launcher = Mock(spec=launch)
        provider = self.makeLXDProvider(lxd_launcher=launcher)
        mock_get_provider.return_value = provider
        execute_run = launcher.return_value.execute_run
        execute_run.return_value = subprocess.CompletedProcess([], 0)
        config = dedent(
            """
            pipeline:
                - test
                - build-wheel

            jobs:
                test:
                    series: focal
                    architectures: [amd64, arm64]
                    run: tox
                build-wheel:
                    series: focal
                    architectures: amd64
                    run: pyproject-build
            """
        )
        Path(".launchpad.yaml").write_text(config)

        result = self.run_command("run")

        self.assertEqual(0, result.exit_code)
        self.assertEqual(
            [
                call(
                    ["lpcraft", "run", "--series", "focal", "test"],
                    cwd=Path("/root/project"),
                    env=None,
                    stdout=ANY,
                    stderr=ANY,
                )
            ],
            execute_run.call_args_list,
        )

    @patch("lpcraft.commands.run.get_provider")
    @patch("lpcraft.commands.run.get_host_architecture", return_value="amd64")
    def test_one_job_fails(
        self, mock_get_host_architecture, mock_get_provider
    ):
        launcher = Mock(spec=launch)
        provider = self.makeLXDProvider(lxd_launcher=launcher)
        mock_get_provider.return_value = provider
        execute_run = launcher.return_value.execute_run
        execute_run.return_value = subprocess.CompletedProcess([], 2)
        config = dedent(
            """
            pipeline:
                - test
                - build-wheel

            jobs:
                test:
                    series: focal
                    architectures: amd64
                    run: tox
                build-wheel:
                    series: focal
                    architectures: amd64
                    run: pyproject-build
            """
        )
        Path(".launchpad.yaml").write_text(config)

        result = self.run_command("run")

        self.assertThat(
            result,
            MatchesStructure.byEquality(
                exit_code=2,
                errors=[
                    CommandError(
                        "Job 'test' for focal/amd64 failed with exit status "
                        "2.",
                        retcode=2,
                    )
                ],
            ),
        )
        execute_run.assert_called_once_with(
            ["lpcraft", "run", "--series", "focal", "test"],
            cwd=Path("/root/project"),
            env=None,
            stdout=ANY,
            stderr=ANY,
        )

    @patch("lpcraft.commands.run.get_provider")
    @patch("lpcraft.commands.run.get_host_architecture", return_value="amd64")
    def test_all_jobs_succeed(
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
                - build-wheel

            jobs:
                test:
                    series: focal
                    architectures: amd64
                    run: tox
                build-wheel:
                    series: bionic
                    architectures: amd64
                    run: pyproject-build
            """
        )
        Path(".launchpad.yaml").write_text(config)

        result = self.run_command("run")

        self.assertEqual(0, result.exit_code)
        self.assertEqual(
            [
                call(
                    ["lpcraft", "run", "--series", "focal", "test"],
                    cwd=Path("/root/project"),
                    env=None,
                    stdout=ANY,
                    stderr=ANY,
                ),
                call(
                    ["lpcraft", "run", "--series", "bionic", "build-wheel"],
                    cwd=Path("/root/project"),
                    env=None,
                    stdout=ANY,
                    stderr=ANY,
                ),
            ],
            execute_run.call_args_list,
        )

    @patch("lpcraft.commands.run.get_provider")
    @patch("lpcraft.commands.run.get_host_architecture", return_value="amd64")
    def test_expands_matrix(
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
                - build-wheel

            jobs:
                test:
                    matrix:
                        - series: bionic
                          architectures: amd64
                        - series: focal
                          architectures: [amd64, s390x]
                    run: tox
                build-wheel:
                    series: bionic
                    architectures: amd64
                    run: pyproject-build
            """
        )
        Path(".launchpad.yaml").write_text(config)

        result = self.run_command("run")

        self.assertEqual(0, result.exit_code)
        self.assertEqual(
            [
                call(
                    ["lpcraft", "run", "--series", "bionic", "test"],
                    cwd=Path("/root/project"),
                    env=None,
                    stdout=ANY,
                    stderr=ANY,
                ),
                call(
                    ["lpcraft", "run", "--series", "focal", "test"],
                    cwd=Path("/root/project"),
                    env=None,
                    stdout=ANY,
                    stderr=ANY,
                ),
                call(
                    ["lpcraft", "run", "--series", "bionic", "build-wheel"],
                    cwd=Path("/root/project"),
                    env=None,
                    stdout=ANY,
                    stderr=ANY,
                ),
            ],
            execute_run.call_args_list,
        )

    @patch("lpcraft.commands.run.get_provider")
    @patch("lpcraft.commands.run.get_host_architecture", return_value="amd64")
    def test_pass_in_environment_variables(
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
                    run: tox
                    environment:
                        TOX_SKIP_ENV: '^(?!lint-)'
            """
        )
        Path(".launchpad.yaml").write_text(config)

        result = self.run_command("run")
        self.assertEqual(0, result.exit_code)

        self.assertEqual(
            [
                call(
                    ["lpcraft", "run", "--series", "focal", "test"],
                    cwd=PosixPath("/root/project"),
                    env={"TOX_SKIP_ENV": "^(?!lint-)"},
                    stdout=ANY,
                    stderr=ANY,
                )
            ],
            execute_run.call_args_list,
        )
