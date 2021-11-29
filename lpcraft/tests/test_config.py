# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

from datetime import timedelta
from pathlib import Path
from textwrap import dedent

from fixtures import TempDir
from pydantic import ValidationError
from testtools import TestCase
from testtools.matchers import (
    Equals,
    MatchesDict,
    MatchesListwise,
    MatchesStructure,
)

from lpcraft.config import Config, OutputDistributeEnum


class TestConfig(TestCase):
    def setUp(self):
        super().setUp()
        self.tempdir = Path(self.useFixture(TempDir()).path)

    def create_config(self, text):
        path = self.tempdir / ".launchpad.yaml"
        path.write_text(text)
        return path

    def test_load(self):
        path = self.create_config(
            dedent(
                """
                pipeline:
                    - test

                jobs:
                    test:
                        series: focal
                        architectures: [amd64, arm64]
                        run: |
                            tox
                """
            )
        )
        config = Config.load(path)
        self.assertThat(
            config,
            MatchesStructure(
                pipeline=Equals(["test"]),
                jobs=MatchesDict(
                    {
                        "test": MatchesListwise(
                            [
                                MatchesStructure.byEquality(
                                    series="focal",
                                    architectures=["amd64", "arm64"],
                                    run="tox\n",
                                )
                            ]
                        )
                    }
                ),
            ),
        )

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
                pipeline=Equals(["test"]),
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
