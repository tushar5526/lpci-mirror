# Copyright 2021 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

from fixtures import MockPatch
from testtools import TestCase


class ProviderBaseTestCase(TestCase):
    def setUp(self):
        super().setUp()
        # Patch out inherited setup steps.
        self.useFixture(
            MockPatch(
                "craft_providers.bases.BuilddBase.setup",
                lambda *args, **kwargs: None,
            )
        )
