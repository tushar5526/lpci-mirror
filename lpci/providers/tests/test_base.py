# Copyright 2022 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

import pytest

from lpci.providers._base import sanitize_lxd_instance_name


@pytest.mark.parametrize(
    "test_input, expected",
    [
        ("et_xmlfile", "et-xmlfile"),  # no underscores
        ("et.xmlfile", "et-xmlfile"),  # no dots
        ("a" * 100, "a" * 63),  # max len is 63
    ],
)
def test_sanitize_lxd_instance_name(test_input, expected):
    assert expected == sanitize_lxd_instance_name(test_input)
