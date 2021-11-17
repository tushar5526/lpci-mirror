# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

from unittest import TestCase

from lpcraft.errors import CommandError


class TestError(TestCase):
    def test_compare_command_error_with_other_type(self):
        """If the other type is not a CommandError, defer eq to other type."""
        self.assertEqual(
            NotImplemented, CommandError("message").__eq__("message")
        )
