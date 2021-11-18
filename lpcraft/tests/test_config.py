# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

from pathlib import Path
from textwrap import dedent

from fixtures import TempDir
from testtools import TestCase
from testtools.matchers import (
    Equals,
    MatchesDict,
    MatchesListwise,
    MatchesStructure,
)

from lpcraft.config import Config


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
        config = Config.load(str(path))
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
        config = Config.load(str(path))
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
        config = Config.load(str(path))
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
