# Copyright 2021-2022 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

import os
from datetime import timedelta
from pathlib import Path
from textwrap import dedent

from fixtures import TempDir
from pydantic import AnyHttpUrl, ValidationError
from testtools import TestCase
from testtools.matchers import (
    Equals,
    MatchesDict,
    MatchesListwise,
    MatchesStructure,
)

from lpcraft.config import Config, OutputDistributeEnum, PackageRepository
from lpcraft.errors import CommandError


class TestConfig(TestCase):
    def setUp(self):
        super().setUp()
        self.tempdir = Path(self.useFixture(TempDir()).path)
        # `Path.cwd()` is assumed as the project directory.
        # So switch to the created project directory.
        os.chdir(self.tempdir)

    def create_config(self, text):
        path = self.tempdir / ".launchpad.yaml"
        path.write_text(text)
        return path

    def test_load_config_not_under_project_dir(self):
        paths_outside_project_dir = [
            "/",
            "/etc/init.d",
            "../../foo",
            "a/b/c/../../../../d",
        ]
        for path in paths_outside_project_dir:
            config_file = Path(path) / "config.yaml"
            self.assertRaises(
                CommandError,
                Config.load,
                config_file,
            )

    def test_load(self):
        path = self.create_config(
            dedent(
                """
                pipeline:
                    - [test]

                jobs:
                    test:
                        series: focal
                        architectures: [amd64, arm64]
                        run-before: pip install --upgrade setuptools build
                        run: |
                            tox
                        run-after: coverage report
                """
            )
        )
        config = Config.load(path)
        self.assertThat(
            config,
            MatchesStructure(
                pipeline=Equals([["test"]]),
                jobs=MatchesDict(
                    {
                        "test": MatchesListwise(
                            [
                                MatchesStructure.byEquality(
                                    series="focal",
                                    architectures=["amd64", "arm64"],
                                    run_before="pip install --upgrade setuptools build",  # noqa:E501
                                    run="tox\n",
                                    run_after="coverage report",
                                )
                            ]
                        )
                    }
                ),
            ),
        )

    def test_load_single_pipeline(self):
        # A single pipeline element can be written as a string, and is
        # automatically wrapped in a list.
        path = self.create_config(
            dedent(
                """
                pipeline:
                    - test

                jobs:
                    test:
                        series: focal
                        architectures: [amd64]
                """
            )
        )
        config = Config.load(path)
        self.assertEqual([["test"]], config.pipeline)

    def test_load_single_architecture(self):
        # A single architecture can be written as a string, and is
        # automatically wrapped in a list.
        path = self.create_config(
            dedent(
                """
                pipeline:
                    - test

                jobs:
                    test:
                        series: focal
                        architectures: amd64
                """
            )
        )
        config = Config.load(path)
        self.assertEqual(["amd64"], config.jobs["test"][0].architectures)

    def test_bad_job_name(self):
        # Job names must be identifiers.
        path = self.create_config(
            dedent(
                """
                pipeline:
                    - foo:bar

                jobs:
                    'foo:bar':
                        series: focal
                        architectures: amd64
                """
            )
        )
        self.assertRaisesRegex(
            ValidationError, r"string does not match regex", Config.load, path
        )

    def test_bad_series_name(self):
        # Series names must be identifiers.
        path = self.create_config(
            dedent(
                """
                pipeline:
                    - test

                jobs:
                    test:
                        series: something/bad
                        architectures: amd64
                """
            )
        )
        self.assertRaisesRegex(
            ValidationError, r"string does not match regex", Config.load, path
        )

    def test_bad_architecture_name(self):
        # Architecture names must be identifiers.
        path = self.create_config(
            dedent(
                """
                pipeline:
                    - test

                jobs:
                    test:
                        series: focal
                        architectures: 'not this'
                """
            )
        )
        self.assertRaisesRegex(
            ValidationError, r"string does not match regex", Config.load, path
        )

    def test_expands_matrix(self):
        path = self.create_config(
            dedent(
                """
                pipeline:
                    - test

                jobs:
                    test:
                        matrix:
                            - series: bionic
                              architectures: [amd64, arm64]

                            - series: focal
                              architectures: amd64
                              run: tox -e py38
                        run: tox
                """
            )
        )
        config = Config.load(path)
        self.assertThat(
            config,
            MatchesStructure(
                pipeline=Equals([["test"]]),
                jobs=MatchesDict(
                    {
                        "test": MatchesListwise(
                            [
                                MatchesStructure.byEquality(
                                    series="bionic",
                                    architectures=["amd64", "arm64"],
                                    run="tox",
                                ),
                                MatchesStructure.byEquality(
                                    series="focal",
                                    architectures=["amd64"],
                                    run="tox -e py38",
                                ),
                            ]
                        )
                    }
                ),
            ),
        )

    def test_load_environment(self):
        path = self.create_config(
            dedent(
                """
                pipeline:
                    - test

                jobs:
                    test:
                        series: focal
                        architectures: amd64
                        environment:
                            ACTIVE: 1
                            SKIP: 0

                """
            )
        )
        config = Config.load(path)
        self.assertEqual(
            {"ACTIVE": "1", "SKIP": "0"}, config.jobs["test"][0].environment
        )

    def test_output(self):
        path = self.create_config(
            dedent(
                """
                pipeline:
                    - build

                jobs:
                    build:
                        series: focal
                        architectures: [amd64]
                        run: pyproject-build
                        output:
                            paths: ["*.whl"]
                            distribute: artifactory
                            channels: [edge]
                            properties:
                                foo: bar
                            dynamic-properties: properties
                            expires: 1:00:00
                """
            )
        )
        config = Config.load(path)
        self.assertThat(
            config.jobs["build"][0].output,
            MatchesStructure.byEquality(
                paths=["*.whl"],
                distribute=OutputDistributeEnum.artifactory,
                channels=["edge"],
                properties={"foo": "bar"},
                dynamic_properties=Path("properties"),
                expires=timedelta(hours=1),
            ),
        )

    def test_output_negative_expires(self):
        path = self.create_config(
            dedent(
                """
                pipeline:
                    - build

                jobs:
                    build:
                        series: focal
                        architectures: [amd64]
                        run: pyproject-build
                        output:
                            expires: -1:00:00
                """
            )
        )
        self.assertRaisesRegex(
            ValidationError,
            r"non-negative duration expected",
            Config.load,
            path,
        )

    def test_input(self):
        path = self.create_config(
            dedent(
                """
                pipeline:
                    - build
                    - test

                jobs:
                    build:
                        series: focal
                        architectures: [amd64]
                        packages: [make]
                        run: make
                        output:
                            paths: [binary]

                    test:
                        series: focal
                        architectures: [amd64]
                        run: artifacts/binary
                        input:
                            job-name: build
                            target-directory: artifacts
                """
            )
        )
        config = Config.load(path)
        self.assertThat(
            config.jobs["test"][0].input,
            MatchesStructure.byEquality(
                job_name="build", target_directory="artifacts"
            ),
        )

    def test_load_snaps(self):
        path = self.create_config(
            dedent(
                """
                pipeline:
                    - test

                jobs:
                    test:
                        series: focal
                        architectures: amd64
                        snaps: [chromium, firefox]
                """
            )
        )
        config = Config.load(path)
        self.assertEqual(["chromium", "firefox"], config.jobs["test"][0].snaps)

    def test_load_config_without_snaps(self):
        path = self.create_config(
            dedent(
                """
                pipeline:
                    - test

                jobs:
                    test:
                        series: focal
                        architectures: amd64
                """
            )
        )
        config = Config.load(path)
        self.assertEqual(None, config.jobs["test"][0].snaps)

    def test_load_package(self):
        path = self.create_config(
            dedent(
                """
                pipeline:
                    - test

                jobs:
                    test:
                        series: focal
                        architectures: amd64
                        packages: [nginx, apache2]
                """
            )
        )
        config = Config.load(path)
        self.assertEqual(["nginx", "apache2"], config.jobs["test"][0].packages)

    def test_load_config_without_packages(self):
        path = self.create_config(
            dedent(
                """
                pipeline:
                    - test

                jobs:
                    test:
                        series: focal
                        architectures: amd64
                """
            )
        )
        config = Config.load(path)
        self.assertEqual(None, config.jobs["test"][0].packages)

    def test_load_plugin(self):
        path = self.create_config(
            dedent(
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
        )

        config = Config.load(path)

        self.assertEqual("tox", config.jobs["test"][0].plugin)

    def test_package_repositories(self):
        path = self.create_config(
            dedent(
                """
                pipeline:
                    - test

                jobs:
                    test:
                        series: focal
                        architectures: amd64
                        packages: [nginx, apache2]
                        package-repositories:
                            - type: apt
                              formats: [deb]
                              components: [main]
                              suites: [focal]
                              url: https://canonical.example.org/artifactory/jammy-golang-backport
                            - type: apt
                              formats: [deb]
                              components: [main]
                              suites: [focal]
                              url: https://canonical.example.org/artifactory/jammy-golang-backport
                              trusted: false
                """  # noqa: E501
            )
        )

        config = Config.load(path)

        self.assertEqual(
            [
                PackageRepository(
                    type="apt",
                    formats=["deb"],
                    components=["main"],
                    suites=["focal"],
                    url=AnyHttpUrl(
                        "https://canonical.example.org/artifactory/jammy-golang-backport",  # noqa: E501
                        scheme="https",
                        host="canonical.example.org",
                        tld="org",
                        host_type="domain",
                        path="/artifactory/jammy-golang-backport",
                    ),
                ),
                PackageRepository(
                    type="apt",
                    formats=["deb"],
                    components=["main"],
                    suites=["focal"],
                    url=AnyHttpUrl(
                        "https://canonical.example.org/artifactory/jammy-golang-backport",  # noqa: E501
                        scheme="https",
                        host="canonical.example.org",
                        tld="org",
                        host_type="domain",
                        path="/artifactory/jammy-golang-backport",
                    ),
                    trusted=False,
                ),
            ],
            config.jobs["test"][0].package_repositories,
        )

    def test_package_repositories_as_string(self):
        path = self.create_config(
            dedent(
                """
                pipeline:
                    - test

                jobs:
                    test:
                        series: focal
                        architectures: amd64
                        packages: [nginx, apache2]
                        package-repositories:
                            - type: apt
                              formats: [deb, deb-src]
                              components: [main]
                              suites: [focal, bionic]
                              url: https://canonical.example.org/artifactory/jammy-golang-backport
                            - type: apt
                              formats: [deb]
                              components: [main]
                              suites: [focal]
                              url: https://canonical.example.org/artifactory/jammy-golang-backport
                              trusted: true
                            - type: apt
                              formats: [deb]
                              components: [main]
                              suites: [focal]
                              url: https://canonical.example.org/artifactory/jammy-golang-backport
                              trusted: false
                """  # noqa: E501
            )
        )
        config = Config.load(path)
        expected = [
            "deb https://canonical.example.org/artifactory/jammy-golang-backport focal main",  # noqa: E501
            "deb https://canonical.example.org/artifactory/jammy-golang-backport bionic main",  # noqa: E501
            "deb-src https://canonical.example.org/artifactory/jammy-golang-backport focal main",  # noqa: E501
            "deb-src https://canonical.example.org/artifactory/jammy-golang-backport bionic main",  # noqa: E501
        ]
        repositories = config.jobs["test"][0].package_repositories
        assert repositories is not None  # workaround necessary to please mypy
        self.assertEqual(
            expected, (list(repositories[0].sources_list_lines()))
        )
        self.assertEqual(
            [
                "deb [trusted=yes] https://canonical.example.org/artifactory/jammy-golang-backport focal main"  # noqa: E501
            ],  # noqa: E501
            list(repositories[1].sources_list_lines()),
        )
        self.assertEqual(
            [
                "deb [trusted=no] https://canonical.example.org/artifactory/jammy-golang-backport focal main"  # noqa: E501
            ],  # noqa: E501
            list(repositories[2].sources_list_lines()),
        )

    def test_specify_license_via_spdx(self):
        path = self.create_config(
            dedent(
                """
                pipeline:
                    - test

                jobs:
                    test:
                        series: focal
                        architectures: amd64
                license:
                    spdx: "MIT"
                """  # noqa: E501
            )
        )
        config = Config.load(path)

        # workaround necessary to please mypy
        assert config.license is not None
        self.assertEqual("MIT", config.license.spdx)

    def test_specify_license_via_path(self):
        path = self.create_config(
            dedent(
                """
                pipeline:
                    - test

                jobs:
                    test:
                        series: focal
                        architectures: amd64
                license:
                    path: LICENSE.txt
                """  # noqa: E501
            )
        )
        config = Config.load(path)

        # workaround necessary to please mypy
        assert config.license is not None
        self.assertEqual("LICENSE.txt", config.license.path)

    def test_license_setting_both_sources_not_allowed(self):
        path = self.create_config(
            dedent(
                """
                pipeline:
                    - test

                jobs:
                    test:
                        series: focal
                        architectures: amd64
                license:
                    spdx: MIT
                    path: LICENSE.txt
                """  # noqa: E501
            )
        )
        self.assertRaisesRegex(
            ValidationError,
            "You cannot set `spdx` and `path` at the same time.",
            Config.load,
            path,
        )
