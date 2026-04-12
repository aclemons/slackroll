import pytest
from slackroll import ChangeLogEntry, changelog_entries_to_bytes, write_raw_output

import tests

if tests.PY2:
    from mock import patch  # type: ignore
else:
    from unittest.mock import patch

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import List


if tests.PY2:
    non_utf8_tld = "\xb3\xb7\xd8\xd9"
else:
    non_utf8_tld = b"\xb3\xb7\xd8\xd9".decode("latin-1")


class FakeBinaryBuffer(object):
    def __init__(self):
        # type: () -> None
        self.output = []  # type: List[bytes]

    def write(self, data):
        # type: (bytes) -> None
        self.output.append(data)

    def flush(self):
        # type: () -> None
        return None

    def close(self):
        # type: () -> None
        return None


class FakeStdout(object):
    def __init__(self):
        # type: () -> None
        self.buffer = FakeBinaryBuffer()
        self.output = []  # type: List[str]

    def isatty(self):
        # type: () -> bool
        return False

    def write(self, data):
        # type: (str) -> None
        self.output.append(data)

    def flush(self):
        # type: () -> None
        return None


class FakePager(object):
    def __init__(self):
        # type: () -> None
        self.stdin = FakeBinaryBuffer()

    def wait(self):
        # type: () -> None
        return None


def test_changelog_entries_to_bytes_preserves_non_utf8_bytes():
    # type: () -> None
    entry = ChangeLogEntry(
        "Tue Feb 17 00:00:00 UTC 2026",
        "  Example non-UTF-8 TLD: %s\n" % non_utf8_tld,
    )

    output = changelog_entries_to_bytes([entry])

    assert b"\xb3\xb7\xd8\xd9" in output


def test_write_raw_output_writes_bytes_to_stdout():
    # type: () -> None
    fake_stdout = FakeStdout()
    payload = b"raw bytes \xb3\xb7\xd8\xd9\n"

    with patch("slackroll.sys.stdout", fake_stdout):
        with patch("slackroll.needs_pager", lambda _lines: False):
            write_raw_output(payload)

    if tests.PY2:
        assert fake_stdout.output == [payload]
    else:
        assert fake_stdout.buffer.output == [payload]


def test_write_raw_output_writes_bytes_to_pager():
    # type: () -> None
    pager = FakePager()
    payload = b"raw bytes \xb3\xb7\xd8\xd9\n"

    with patch("slackroll.needs_pager", lambda _lines: True):
        with patch("slackroll.call_pager", lambda: pager):
            write_raw_output(payload)

    assert pager.stdin.output == [payload]
