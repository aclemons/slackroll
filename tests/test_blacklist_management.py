# -*- coding: utf-8 -*-

import os
import re

import pytest
from slackroll import (
    add_blacklist_exprs,
    compile_blacklist_regexp,
    del_blacklist_exprs,
    get_blacklist,
    get_blacklist_re,
    normalise_blacklist_entry,
    print_blacklist,
    slackroll_blacklist_filename,
    try_dump,
    try_load,
)

import tests

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import List


non_ascii_text = tests.decode_bytes_literal("\xc3\xa4\xc3\xb6\xc3\xbc", "utf-8")


@pytest.fixture  # type: ignore
def blacklist():
    # type: () -> List[str]
    return ["entry1", "entry2", "entry3@myrepo", "äöü"]


def test_get_blacklist_re(blacklist, request):
    # type: (List[str], pytest.FixtureRequest) -> None
    get_blacklist_mock = tests.start_patch(request, "slackroll.get_blacklist")
    get_blacklist_mock.return_value = blacklist

    res = get_blacklist_re()

    assert len(res) == 4
    assert (re.compile("entry1"), re.compile("")) == res[0]
    assert (re.compile("entry2"), re.compile("")) == res[1]
    assert (re.compile("entry3"), re.compile("myrepo")) == res[2]
    multibyte_text = (
        tests.bytes_literal("\xc3\xa4\xc3\xb6\xc3\xbc")
        if tests.PY2
        else tests.decode_bytes_literal("\xc3\xa4\xc3\xb6\xc3\xbc", "latin-1")
    )
    assert res[3][0].search(multibyte_text) is not None
    assert res[3][1].pattern == ""


def test_print_blacklist(blacklist, request):
    # type: (List[str], pytest.FixtureRequest) -> None
    get_blacklist_mock = tests.start_patch(request, "slackroll.get_blacklist")
    print_list_or_mock = tests.start_patch(request, "slackroll.print_list_or")
    get_blacklist_mock.return_value = blacklist

    print_blacklist()

    print_list_or_mock.assert_called_with(
        ["0     entry1", "1     entry2", "2     entry3@myrepo", "3     äöü"],
        "Blacklisted expressions:",
        "No blacklisted expressions",
    )


def test_add_blacklist_exprs(blacklist, request):
    # type: (List[str], pytest.FixtureRequest) -> None
    get_blacklist_mock = tests.start_patch(request, "slackroll.get_blacklist")
    try_dump_mock = tests.start_patch(request, "slackroll.try_dump")
    get_blacklist_mock.return_value = blacklist

    add_blacklist_exprs(["newentry1", "newentry2"])

    try_dump_mock.assert_called_with(
        ["entry1", "entry2", "entry3@myrepo", "äöü", "newentry1", "newentry2"],
        slackroll_blacklist_filename,
    )


def test_add_blacklist_exprs_preserves_multibyte_display_text(request):
    # type: (pytest.FixtureRequest) -> None
    get_blacklist_mock = tests.start_patch(request, "slackroll.get_blacklist")
    try_dump_mock = tests.start_patch(request, "slackroll.try_dump")
    get_blacklist_mock.return_value = []

    add_blacklist_exprs(["Főtanúsítvány@https://example.invalid/Főtanúsítvány"])

    try_dump_mock.assert_called_with(
        ["Főtanúsítvány@https://example.invalid/Főtanúsítvány"],
        slackroll_blacklist_filename,
    )


def test_add_blacklist_exprs_invalid(blacklist, request):
    # type: (List[str], pytest.FixtureRequest) -> None
    get_blacklist_mock = tests.start_patch(request, "slackroll.get_blacklist")
    exit_mock = tests.start_patch(request, "sys.exit")
    get_blacklist_mock.return_value = blacklist
    exit_mock.side_effect = ValueError("boom")

    pytest.raises(ValueError, add_blacklist_exprs, ["test@[\\]"])

    exit_mock.assert_called_with('ERROR: "test@[\\]" is an invalid regular expression')


def test_add_blacklist_exprs_invalid_url_regex(blacklist, request):
    # type: (List[str], pytest.FixtureRequest) -> None
    get_blacklist_mock = tests.start_patch(request, "slackroll.get_blacklist")
    exit_mock = tests.start_patch(request, "sys.exit")
    get_blacklist_mock.return_value = blacklist
    exit_mock.side_effect = ValueError

    pytest.raises(ValueError, add_blacklist_exprs, ["[\\]"])

    exit_mock.assert_called_with('ERROR: "[\\]" is an invalid regular expression')


def test_del_blacklist_exprs(blacklist, request):
    # type: (List[str], pytest.FixtureRequest) -> None
    get_blacklist_mock = tests.start_patch(request, "slackroll.get_blacklist")
    try_dump_mock = tests.start_patch(request, "slackroll.try_dump")
    get_blacklist_mock.return_value = blacklist

    del_blacklist_exprs(["0"])

    try_dump_mock.assert_called_with(
        ["entry2", "entry3@myrepo", "äöü"], slackroll_blacklist_filename
    )


def test_del_blacklist_exprs_multiple(blacklist, request):
    # type: (List[str], pytest.FixtureRequest) -> None
    get_blacklist_mock = tests.start_patch(request, "slackroll.get_blacklist")
    try_dump_mock = tests.start_patch(request, "slackroll.try_dump")
    get_blacklist_mock.return_value = blacklist

    del_blacklist_exprs(["0", "1"])

    try_dump_mock.assert_called_with(
        ["entry3@myrepo", "äöü"], slackroll_blacklist_filename
    )


def test_del_blacklist_exprs_invalid_index_negative(blacklist, request):
    # type: (List[str], pytest.FixtureRequest) -> None
    get_blacklist_mock = tests.start_patch(request, "slackroll.get_blacklist")
    exit_mock = tests.start_patch(request, "sys.exit")
    get_blacklist_mock.return_value = blacklist
    exit_mock.side_effect = ValueError

    pytest.raises(ValueError, del_blacklist_exprs, ["-1"])

    exit_mock.assert_called_with("ERROR: invalid blacklist entry index: -1")


def test_del_blacklist_exprs_invalid_index_exceeds_length(blacklist, request):
    # type: (List[str], pytest.FixtureRequest) -> None
    get_blacklist_mock = tests.start_patch(request, "slackroll.get_blacklist")
    exit_mock = tests.start_patch(request, "sys.exit")
    get_blacklist_mock.return_value = blacklist
    exit_mock.side_effect = ValueError

    pytest.raises(ValueError, del_blacklist_exprs, ["4"])

    exit_mock.assert_called_with("ERROR: invalid blacklist entry index: 4")


def test_get_blacklist_from_py2_pickle(blacklist, request):
    # type: (List[str], pytest.FixtureRequest) -> None
    """Checks if we can deserialise a known good file."""

    data_file = os.path.join(
        os.path.dirname(__file__), "..", "data", "py2_blacklist.db"
    )

    tests.start_patch(request, "slackroll.slackroll_blacklist_filename", data_file)
    assert blacklist == get_blacklist()


def test_get_blacklist_normalises_utf8_bytes(blacklist, request):
    # type: (List[str], pytest.FixtureRequest) -> None
    f = tests.named_temporary_file(delete=False)
    f.close()
    os.unlink(f.name)

    try:
        tests.start_patch(request, "slackroll.slackroll_blacklist_filename", f.name)
        try_dump(
            [
                tests.bytes_literal("entry1"),
                tests.bytes_literal("entry2"),
                tests.bytes_literal("entry3@myrepo"),
                non_ascii_text.encode("utf-8"),
            ],
            f.name,
        )
        assert blacklist == get_blacklist()
    finally:
        if os.path.exists(f.name):
            os.unlink(f.name)


def test_normalise_blacklist_entry_non_utf8_bytes_uses_latin1_fallback():
    # type: () -> None
    normalised = normalise_blacklist_entry(non_ascii_text.encode("latin-1"))

    if tests.PY2:
        assert normalised == non_ascii_text.encode("latin-1")
    else:
        assert normalised == non_ascii_text


def test_compile_blacklist_regexp_matches_lossless_multibyte_text():
    # type: () -> None
    lossless_text = (
        tests.bytes_literal("F\xc5\x91tan\xc3\xbas\xc3\xadtv\xc3\xa1ny")
        if tests.PY2
        else tests.decode_bytes_literal(
            "F\xc5\x91tan\xc3\xbas\xc3\xadtv\xc3\xa1ny",
            "latin-1",
        )
    )

    assert compile_blacklist_regexp("Főtanúsítvány").search(lossless_text) is not None


def test_get_blacklist_re_matches_lossless_package_and_url_text(request):
    # type: (pytest.FixtureRequest) -> None
    get_blacklist_mock = tests.start_patch(request, "slackroll.get_blacklist")
    get_blacklist_mock.return_value = [
        "Főtanúsítvány@https://example.invalid/Főtanúsítvány"
    ]

    pkg_regex, url_regex = get_blacklist_re()[0]
    pkg_text = (
        tests.bytes_literal("ca-certificates-F\xc5\x91tan\xc3\xbas\xc3\xadtv\xc3\xa1ny")
        if tests.PY2
        else tests.decode_bytes_literal(
            "ca-certificates-F\xc5\x91tan\xc3\xbas\xc3\xadtv\xc3\xa1ny",
            "latin-1",
        )
    )
    url_text = (
        tests.bytes_literal(
            "https://example.invalid/F\xc5\x91tan\xc3\xbas\xc3\xadtv\xc3\xa1ny"
        )
        if tests.PY2
        else tests.decode_bytes_literal(
            "https://example.invalid/F\xc5\x91tan\xc3\xbas\xc3\xadtv\xc3\xa1ny",
            "latin-1",
        )
    )

    assert pkg_regex.search(pkg_text) is not None
    assert url_regex.search(url_text) is not None


def test_round_trip_serialisation_bl(blacklist, request):
    # type: (List[str], pytest.FixtureRequest) -> None
    """Checks if we can round trip serialise then deserialise a value."""

    f = tests.named_temporary_file(delete=False)
    f.close()
    os.unlink(f.name)

    try:
        tests.start_patch(request, "slackroll.slackroll_blacklist_filename", f.name)
        add_blacklist_exprs(blacklist)

        assert blacklist == try_load(f.name)
        assert blacklist == get_blacklist()
    finally:
        if os.path.exists(f.name):
            os.unlink(f.name)
