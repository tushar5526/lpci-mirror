# Copyright 2023 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

import io

from systemfixtures import FakeProcesses
from testtools import TestCase

from lpci.git import get_current_branch, get_current_remote_url


class TestGetCurrentBranch(TestCase):
    def test_has_no_current_branch(self):
        processes_fixture = self.useFixture(FakeProcesses())
        processes_fixture.add(
            lambda _: {"stdout": io.StringIO("\n")}, name="git"
        )

        self.assertIsNone(get_current_branch())

        self.assertEqual(
            [["git", "branch", "--show-current"]],
            [proc._args["args"] for proc in processes_fixture.procs],
        )

    def test_has_current_branch(self):
        processes_fixture = self.useFixture(FakeProcesses())
        processes_fixture.add(
            lambda _: {"stdout": io.StringIO("feature\n")}, name="git"
        )

        self.assertEqual("feature", get_current_branch())

        self.assertEqual(
            [["git", "branch", "--show-current"]],
            [proc._args["args"] for proc in processes_fixture.procs],
        )


class TestGetCurrentRemoteURL(TestCase):
    def test_has_no_current_branch(self):
        processes_fixture = self.useFixture(FakeProcesses())
        processes_fixture.add(
            lambda _: {"stdout": io.StringIO("\n")}, name="git"
        )

        self.assertIsNone(get_current_remote_url())

        self.assertEqual(
            [["git", "branch", "--show-current"]],
            [proc._args["args"] for proc in processes_fixture.procs],
        )

    def test_has_no_current_remote(self):
        def fake_git(args):
            if args["args"][1] == "branch":
                return {"stdout": io.StringIO("feature\n")}
            elif args["args"][1] == "config":
                return {"stdout": io.StringIO("\n")}
            else:  # pragma: no cover
                return {"returncode": 1}

        processes_fixture = self.useFixture(FakeProcesses())
        processes_fixture.add(fake_git, name="git")

        self.assertIsNone(get_current_remote_url())
        self.assertEqual(
            [
                ["git", "branch", "--show-current"],
                ["git", "config", "branch.feature.remote"],
            ],
            [proc._args["args"] for proc in processes_fixture.procs],
        )

    def test_has_current_remote(self):
        def fake_git(args):
            if args["args"][1] == "branch":
                return {"stdout": io.StringIO("feature\n")}
            elif args["args"][1] == "config":
                return {"stdout": io.StringIO("origin\n")}
            elif args["args"][1] == "remote":
                return {"stdout": io.StringIO("git+ssh://git.example.com/\n")}
            else:  # pragma: no cover
                return {"returncode": 1}

        processes_fixture = self.useFixture(FakeProcesses())
        processes_fixture.add(fake_git, name="git")

        self.assertEqual(
            "git+ssh://git.example.com/", get_current_remote_url()
        )
        self.assertEqual(
            [
                ["git", "branch", "--show-current"],
                ["git", "config", "branch.feature.remote"],
                ["git", "remote", "get-url", "origin"],
            ],
            [proc._args["args"] for proc in processes_fixture.procs],
        )
