# Copyright 2023 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

import io
from datetime import datetime
from pathlib import Path

from fixtures import MockPatchObject
from launchpadlib.launchpad import Launchpad
from launchpadlib.testing.launchpad import FakeLaunchpad
from systemfixtures import FakeProcesses
from testtools.matchers import Equals, MatchesListwise, MatchesStructure
from wadllib.application import Application

from lpci.commands.tests import CommandBaseTestCase
from lpci.errors import CommandError


class TestRelease(CommandBaseTestCase):
    def setUp(self):
        super().setUp()
        self.uploads = []

    def set_up_local_branch(
        self, branch_name: str, remote_name: str, url: str
    ) -> None:
        def fake_git(args):
            if args["args"][1] == "branch":
                return {"stdout": io.StringIO(f"{branch_name}\n")}
            elif args["args"][1] == "config":
                return {"stdout": io.StringIO(f"{remote_name}\n")}
            elif args["args"][1] == "remote":
                return {"stdout": io.StringIO(f"{url}\n")}
            else:  # pragma: no cover
                return {"returncode": 1}

        processes_fixture = self.useFixture(FakeProcesses())
        processes_fixture.add(fake_git, name="git")

    def make_fake_launchpad(self) -> FakeLaunchpad:
        lp = FakeLaunchpad(
            application=Application(
                "https://api.launchpad.net/devel/",
                (Path(__file__).parent / "launchpad-wadl.xml").read_bytes(),
            )
        )
        self.useFixture(
            MockPatchObject(
                Launchpad, "login_with", lambda *args, **kwargs: lp
            )
        )
        return lp

    def fake_upload(self, ci_build, to_series, to_pocket, to_channel):
        self.uploads.append((ci_build, to_series, to_pocket, to_channel))

    def test_no_repository_argument_and_no_remote_branch(self):
        processes_fixture = self.useFixture(FakeProcesses())
        processes_fixture.add(
            lambda _: {"stdout": io.StringIO("\n")}, name="git"
        )

        result = self.run_command(
            "release", "ppa:owner/ubuntu/name", "focal", "edge"
        )

        self.assertThat(
            result,
            MatchesStructure.byEquality(
                exit_code=1,
                errors=[
                    CommandError(
                        "No --repository option was given, and the current "
                        "branch does not track a remote branch."
                    )
                ],
            ),
        )

    def test_no_repository_argument_and_remote_branch_on_bad_host(self):
        self.set_up_local_branch(
            "feature", "origin", "git+ssh://git.example.com/"
        )

        result = self.run_command(
            "release", "ppa:owner/ubuntu/name", "focal", "edge"
        )

        self.assertThat(
            result,
            MatchesStructure.byEquality(
                exit_code=1,
                errors=[
                    CommandError(
                        "No --repository option was given, and the current "
                        "branch does not track a remote branch on "
                        "git.launchpad.net."
                    )
                ],
            ),
        )

    def test_no_commit_argument_and_no_current_branch(self):
        processes_fixture = self.useFixture(FakeProcesses())
        processes_fixture.add(
            lambda _: {"stdout": io.StringIO("\n")}, name="git"
        )

        result = self.run_command(
            "release",
            "--repository",
            "example",
            "ppa:owner/ubuntu/name",
            "focal",
            "edge",
        )

        self.assertThat(
            result,
            MatchesStructure.byEquality(
                exit_code=1,
                errors=[
                    CommandError(
                        "No --commit option was given, and there is no "
                        "current branch."
                    )
                ],
            ),
        )

    def test_repository_does_not_exist(self):
        lp = self.make_fake_launchpad()
        lp.git_repositories = {"getByPath": lambda path: None}

        result = self.run_command(
            "release",
            "--repository",
            "example",
            "--commit",
            "missing",
            "ppa:owner/ubuntu/name",
            "focal",
            "edge",
        )

        self.assertThat(
            result,
            MatchesStructure.byEquality(
                exit_code=1,
                errors=[
                    CommandError(
                        "Repository example does not exist on Launchpad."
                    )
                ],
            ),
        )

    def test_no_branch_or_tag(self):
        lp = self.make_fake_launchpad()
        lp.git_repositories = {
            "getByPath": lambda path: {"getRefByPath": lambda path: None}
        }

        result = self.run_command(
            "release",
            "--repository",
            "example",
            "--commit",
            "missing",
            "ppa:owner/ubuntu/name",
            "focal",
            "edge",
        )

        self.assertThat(
            result,
            MatchesStructure.byEquality(
                exit_code=1,
                errors=[
                    CommandError("example has no branch or tag named missing.")
                ],
            ),
        )

    def test_no_completed_ci_builds(self):
        lp = self.make_fake_launchpad()
        commit_sha1 = "1" * 40
        lp.git_repositories = {
            "getByPath": lambda path: {
                "getRefByPath": lambda path: {"commit_sha1": commit_sha1},
                "getStatusReports": lambda commit_sha1: {
                    "entries": [{"ci_build": {"buildstate": "Needs building"}}]
                },
            }
        }

        result = self.run_command(
            "release",
            "--repository",
            "example",
            "--commit",
            "branch",
            "ppa:owner/ubuntu/name",
            "focal",
            "edge",
        )

        self.assertThat(
            result,
            MatchesStructure.byEquality(
                exit_code=1,
                errors=[
                    CommandError(
                        f"example:{commit_sha1} has no completed CI builds "
                        f"with attached files."
                    )
                ],
            ),
        )

    def test_no_ci_builds_with_artifacts(self):
        lp = self.make_fake_launchpad()
        commit_sha1 = "1" * 40
        lp.git_repositories = {
            "getByPath": lambda path: {
                "getRefByPath": lambda path: {"commit_sha1": commit_sha1},
                "getStatusReports": lambda commit_sha1: {
                    "entries": [
                        {
                            "ci_build": {"buildstate": "Successfully built"},
                            "getArtifactURLs": lambda artifact_type: [],
                        }
                    ]
                },
            }
        }

        result = self.run_command(
            "release",
            "--repository",
            "example",
            "--commit",
            "branch",
            "ppa:owner/ubuntu/name",
            "focal",
            "edge",
        )

        self.assertThat(
            result,
            MatchesStructure.byEquality(
                exit_code=1,
                errors=[
                    CommandError(
                        f"example:{commit_sha1} has no completed CI builds "
                        f"with attached files."
                    )
                ],
            ),
        )

    def test_dry_run(self):
        lp = self.make_fake_launchpad()
        commit_sha1 = "1" * 40
        lp.git_repositories = {
            "getByPath": lambda path: {
                "getRefByPath": lambda path: {"commit_sha1": commit_sha1},
                "getStatusReports": lambda commit_sha1: {
                    "entries": [
                        {
                            "ci_build": {
                                "arch_tag": "amd64",
                                "buildstate": "Successfully built",
                                "datebuilt": datetime(2022, 1, 1, 0, 0, 0),
                            },
                            "getArtifactURLs": lambda artifact_type: ["url"],
                        }
                    ]
                },
            }
        }
        lp.archives = {
            "getByReference": lambda reference: {
                "uploadCIBuild": self.fake_upload
            }
        }

        result = self.run_command(
            "release",
            "--dry-run",
            "--repository",
            "example",
            "--commit",
            "branch",
            "ppa:owner/ubuntu/name",
            "focal",
            "edge",
        )

        self.assertThat(
            result,
            MatchesStructure.byEquality(
                exit_code=0,
                messages=[
                    f"Would release amd64 build of example:{commit_sha1} to "
                    f"ppa:owner/ubuntu/name focal edge."
                ],
            ),
        )
        self.assertEqual([], self.uploads)

    def test_release(self):
        lp = self.make_fake_launchpad()
        commit_sha1 = "1" * 40
        lp.git_repositories = {
            "getByPath": lambda path: {
                "getRefByPath": lambda path: {"commit_sha1": commit_sha1},
                "getStatusReports": lambda commit_sha1: {
                    "entries": [
                        {
                            "ci_build": {
                                "arch_tag": "amd64",
                                "buildstate": "Successfully built",
                                "datebuilt": datetime(2022, 1, 1, 0, 0, 0),
                            },
                            "getArtifactURLs": lambda artifact_type: ["url"],
                        },
                        {
                            "ci_build": {
                                "arch_tag": "amd64",
                                "buildstate": "Successfully built",
                                "datebuilt": datetime(2022, 1, 1, 12, 0, 0),
                            },
                            "getArtifactURLs": lambda artifact_type: ["url"],
                        },
                    ]
                },
            }
        }
        lp.archives = {
            "getByReference": lambda reference: {
                "uploadCIBuild": self.fake_upload
            }
        }

        result = self.run_command(
            "release",
            "--repository",
            "example",
            "--commit",
            "branch",
            "ppa:owner/ubuntu/name",
            "focal",
            "edge",
        )

        self.assertThat(
            result,
            MatchesStructure.byEquality(
                exit_code=0,
                messages=[
                    f"Released amd64 build of example:{commit_sha1} to "
                    f"ppa:owner/ubuntu/name focal edge."
                ],
            ),
        )
        [upload] = self.uploads
        self.assertThat(
            upload,
            MatchesListwise(
                [
                    MatchesStructure.byEquality(
                        arch_tag="amd64",
                        datebuilt=datetime(2022, 1, 1, 12, 0, 0),
                    ),
                    Equals("focal"),
                    Equals("Release"),
                    Equals("edge"),
                ]
            ),
        )

    def test_release_with_commit_id(self):
        lp = self.make_fake_launchpad()
        commit_sha1 = "1" * 40
        lp.git_repositories = {
            "getByPath": lambda path: {
                "getStatusReports": lambda commit_sha1: {
                    "entries": [
                        {
                            "ci_build": {
                                "arch_tag": "amd64",
                                "buildstate": "Successfully built",
                                "datebuilt": datetime(2022, 1, 1, 0, 0, 0),
                            },
                            "getArtifactURLs": lambda artifact_type: ["url"],
                        },
                        {
                            "ci_build": {
                                "arch_tag": "amd64",
                                "buildstate": "Successfully built",
                                "datebuilt": datetime(2022, 1, 1, 12, 0, 0),
                            },
                            "getArtifactURLs": lambda artifact_type: ["url"],
                        },
                    ]
                },
            }
        }
        lp.archives = {
            "getByReference": lambda reference: {
                "uploadCIBuild": self.fake_upload
            }
        }

        result = self.run_command(
            "release",
            "--repository",
            "example",
            "--commit",
            commit_sha1,
            "ppa:owner/ubuntu/name",
            "focal",
            "edge",
        )

        self.assertThat(
            result,
            MatchesStructure.byEquality(
                exit_code=0,
                messages=[
                    f"Released amd64 build of example:{commit_sha1} to "
                    f"ppa:owner/ubuntu/name focal edge."
                ],
            ),
        )

    def test_release_from_current_branch(self):
        self.set_up_local_branch(
            "feature", "origin", "git+ssh://git.launchpad.net/example"
        )
        lp = self.make_fake_launchpad()
        commit_sha1 = "1" * 40
        lp.git_repositories = {
            "getByPath": lambda path: {
                "getRefByPath": lambda path: {"commit_sha1": commit_sha1},
                "getStatusReports": lambda commit_sha1: {
                    "entries": [
                        {
                            "ci_build": {
                                "arch_tag": "amd64",
                                "buildstate": "Successfully built",
                                "datebuilt": datetime(2022, 1, 1, 0, 0, 0),
                            },
                            "getArtifactURLs": lambda artifact_type: ["url"],
                        }
                    ]
                },
            }
        }
        lp.archives = {
            "getByReference": lambda reference: {
                "uploadCIBuild": self.fake_upload
            }
        }

        result = self.run_command(
            "release",
            "ppa:owner/ubuntu/name",
            "focal",
            "edge",
        )

        self.assertThat(
            result,
            MatchesStructure.byEquality(
                exit_code=0,
                messages=[
                    f"Released amd64 build of example:{commit_sha1} to "
                    f"ppa:owner/ubuntu/name focal edge."
                ],
            ),
        )

    def test_release_from_current_branch_with_username(self):
        self.set_up_local_branch(
            "feature", "origin", "git+ssh://username@git.launchpad.net/example"
        )
        lp = self.make_fake_launchpad()
        commit_sha1 = "1" * 40
        lp.git_repositories = {
            "getByPath": lambda path: {
                "getRefByPath": lambda path: {"commit_sha1": commit_sha1},
                "getStatusReports": lambda commit_sha1: {
                    "entries": [
                        {
                            "ci_build": {
                                "arch_tag": "amd64",
                                "buildstate": "Successfully built",
                                "datebuilt": datetime(2022, 1, 1, 0, 0, 0),
                            },
                            "getArtifactURLs": lambda artifact_type: ["url"],
                        }
                    ]
                },
            }
        }
        lp.archives = {
            "getByReference": lambda reference: {
                "uploadCIBuild": self.fake_upload
            }
        }

        result = self.run_command(
            "release",
            "ppa:owner/ubuntu/name",
            "focal",
            "edge",
        )

        self.assertThat(
            result,
            MatchesStructure.byEquality(
                exit_code=0,
                messages=[
                    f"Released amd64 build of example:{commit_sha1} to "
                    f"ppa:owner/ubuntu/name focal edge."
                ],
            ),
        )

    def test_release_multiple_architectures(self):
        lp = self.make_fake_launchpad()
        commit_sha1 = "1" * 40
        lp.git_repositories = {
            "getByPath": lambda path: {
                "getRefByPath": lambda path: {"commit_sha1": commit_sha1},
                "getStatusReports": lambda commit_sha1: {
                    "entries": [
                        {
                            "ci_build": {
                                "arch_tag": "amd64",
                                "buildstate": "Successfully built",
                                "datebuilt": datetime(2022, 1, 1, 0, 0, 0),
                            },
                            "getArtifactURLs": lambda artifact_type: ["url"],
                        },
                        {
                            "ci_build": {
                                "arch_tag": "arm64",
                                "buildstate": "Successfully built",
                                "datebuilt": datetime(2022, 1, 1, 1, 0, 0),
                            },
                            "getArtifactURLs": lambda artifact_type: ["url"],
                        },
                        {
                            "ci_build": {
                                "arch_tag": "amd64",
                                "buildstate": "Successfully built",
                                "datebuilt": datetime(2022, 1, 1, 12, 0, 0),
                            },
                            "getArtifactURLs": lambda artifact_type: ["url"],
                        },
                        {
                            "ci_build": {
                                "arch_tag": "arm64",
                                "buildstate": "Successfully built",
                                "datebuilt": datetime(2022, 1, 1, 13, 0, 0),
                            },
                            "getArtifactURLs": lambda artifact_type: ["url"],
                        },
                    ]
                },
            }
        }
        lp.archives = {
            "getByReference": lambda reference: {
                "uploadCIBuild": self.fake_upload
            }
        }

        result = self.run_command(
            "release",
            "--repository",
            "example",
            "--commit",
            "branch",
            "ppa:owner/ubuntu/name",
            "focal",
            "edge",
        )

        self.assertThat(
            result,
            MatchesStructure.byEquality(
                exit_code=0,
                messages=[
                    f"Released amd64 build of example:{commit_sha1} to "
                    f"ppa:owner/ubuntu/name focal edge.",
                    f"Released arm64 build of example:{commit_sha1} to "
                    f"ppa:owner/ubuntu/name focal edge.",
                ],
            ),
        )
        self.assertThat(
            self.uploads,
            MatchesListwise(
                [
                    MatchesListwise(
                        [
                            MatchesStructure.byEquality(
                                arch_tag="amd64",
                                datebuilt=datetime(2022, 1, 1, 12, 0, 0),
                            ),
                            Equals("focal"),
                            Equals("Release"),
                            Equals("edge"),
                        ]
                    ),
                    MatchesListwise(
                        [
                            MatchesStructure.byEquality(
                                arch_tag="arm64",
                                datebuilt=datetime(2022, 1, 1, 13, 0, 0),
                            ),
                            Equals("focal"),
                            Equals("Release"),
                            Equals("edge"),
                        ],
                    ),
                ]
            ),
        )

    def test_release_select_single_architecture(self):
        lp = self.make_fake_launchpad()
        commit_sha1 = "1" * 40
        lp.git_repositories = {
            "getByPath": lambda path: {
                "getRefByPath": lambda path: {"commit_sha1": commit_sha1},
                "getStatusReports": lambda commit_sha1: {
                    "entries": [
                        {
                            "ci_build": {
                                "arch_tag": "amd64",
                                "buildstate": "Successfully built",
                                "datebuilt": datetime(2022, 1, 1, 0, 0, 0),
                            },
                            "getArtifactURLs": lambda artifact_type: ["url"],
                        },
                        {
                            "ci_build": {
                                "arch_tag": "arm64",
                                "buildstate": "Successfully built",
                                "datebuilt": datetime(2022, 1, 1, 1, 0, 0),
                            },
                            "getArtifactURLs": lambda artifact_type: ["url"],
                        },
                        {
                            "ci_build": {
                                "arch_tag": "amd64",
                                "buildstate": "Successfully built",
                                "datebuilt": datetime(2022, 1, 1, 12, 0, 0),
                            },
                            "getArtifactURLs": lambda artifact_type: ["url"],
                        },
                        {
                            "ci_build": {
                                "arch_tag": "arm64",
                                "buildstate": "Successfully built",
                                "datebuilt": datetime(2022, 1, 1, 13, 0, 0),
                            },
                            "getArtifactURLs": lambda artifact_type: ["url"],
                        },
                    ]
                },
            }
        }
        lp.archives = {
            "getByReference": lambda reference: {
                "uploadCIBuild": self.fake_upload
            }
        }

        result = self.run_command(
            "release",
            "--repository",
            "example",
            "--commit",
            "branch",
            "--architecture",
            "amd64",
            "ppa:owner/ubuntu/name",
            "focal",
            "edge",
        )

        self.assertThat(
            result,
            MatchesStructure.byEquality(
                exit_code=0,
                messages=[
                    f"Released amd64 build of example:{commit_sha1} to "
                    f"ppa:owner/ubuntu/name focal edge.",
                ],
            ),
        )
        [upload] = self.uploads
        self.assertThat(
            upload,
            MatchesListwise(
                [
                    MatchesStructure.byEquality(
                        arch_tag="amd64",
                        datebuilt=datetime(2022, 1, 1, 12, 0, 0),
                    ),
                    Equals("focal"),
                    Equals("Release"),
                    Equals("edge"),
                ]
            ),
        )
