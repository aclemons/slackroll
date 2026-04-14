import os
import shutil
from tempfile import mkdtemp

import pytest
from slackroll import get_changelog, slackroll_changelog_filename, update_changelog

import tests

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import List


@pytest.fixture  # type: ignore
def temp_dir(request):
    # type: (pytest.FixtureRequest) -> str
    dir = mkdtemp()

    def teardown():
        # type: () -> None
        shutil.rmtree(dir)

    request.addfinalizer(teardown)
    return dir


def assert_text_preserves_bytes(text, expected_bytes):
    # type: (str, bytes) -> None
    if tests.PY2:
        assert expected_bytes in text
        return

    assert text.encode("latin-1").find(expected_bytes) != -1


def test_update_changelog_full_preserves_non_utf8_bytes(temp_dir, request):
    # type: (str, pytest.FixtureRequest) -> None
    changelog_db = os.path.join(temp_dir, "changelog.db")
    payload = (
        tests.bytes_literal("Tue Feb 17 00:00:00 UTC 2026\n")
        + tests.bytes_literal(
            "  Thanks to contributor \xb3\xb7\xd8\xd9 for the report.\n"
        )
        + tests.bytes_literal("+--------------------------+\n")
    )

    def fake_download_or_exit(_mirror, _filename, destination):
        # type: (str, str, str) -> None
        local_filename = os.path.join(destination, slackroll_changelog_filename)
        handle = open(local_filename, "wb")
        try:
            handle.write(payload)
        finally:
            handle.close()

    tests.start_patch(request, "slackroll.get_temp_dir", lambda: temp_dir)
    tests.start_patch(request, "slackroll.slackroll_local_changelog", changelog_db)
    tests.start_patch(request, "slackroll.download_or_exit", fake_download_or_exit)
    assert update_changelog("https://example.invalid/", full=True) is True

    changelog = get_changelog()

    assert changelog.num_batches() == 1
    assert changelog.last_batch()[0].timestamp == "Tue Feb 17 00:00:00 UTC 2026"
    assert_text_preserves_bytes(
        changelog.last_batch()[0].text,
        tests.bytes_literal("\xb3\xb7\xd8\xd9"),
    )


def test_update_changelog_incremental_preserves_non_utf8_bytes(temp_dir, request):
    # type: (str, pytest.FixtureRequest) -> None
    changelog_db = os.path.join(temp_dir, "changelog.db")
    initial_payload = (
        tests.bytes_literal("Mon Feb 16 00:00:00 UTC 2026\n")
        + tests.bytes_literal("  Existing entry\n")
        + tests.bytes_literal("+--------------------------+\n")
    )
    new_lines = [
        tests.bytes_literal("Tue Feb 17 00:00:00 UTC 2026\n"),
        tests.bytes_literal(
            "  Thanks to contributor \xb3\xb7\xd8\xd9 for the report.\n"
        ),
        tests.bytes_literal("+--------------------------+\n"),
        tests.bytes_literal("Mon Feb 16 00:00:00 UTC 2026\n"),
    ]

    def fake_download_or_exit(_mirror, _filename, destination):
        # type: (str, str, str) -> None
        local_filename = os.path.join(destination, slackroll_changelog_filename)
        handle = open(local_filename, "wb")
        try:
            handle.write(initial_payload)
        finally:
            handle.close()

    class FakeResponse(object):
        def __init__(self, lines):
            # type: (List[bytes]) -> None
            self._lines = list(lines)

        def readline(self):
            # type: () -> bytes
            if len(self._lines) == 0:
                return tests.bytes_literal("")
            return self._lines.pop(0)

        def close(self):
            # type: () -> None
            return None

    tests.start_patch(request, "slackroll.get_temp_dir", lambda: temp_dir)
    tests.start_patch(request, "slackroll.slackroll_local_changelog", changelog_db)
    tests.start_patch(request, "slackroll.download_or_exit", fake_download_or_exit)
    assert update_changelog("https://example.invalid/", full=True) is True

    tests.start_patch(
        request, "slackroll.urlopen", lambda _url: FakeResponse(new_lines)
    )
    assert update_changelog("https://example.invalid/") is True

    changelog = get_changelog()

    assert changelog.num_batches() == 2
    assert changelog.last_batch()[0].timestamp == "Tue Feb 17 00:00:00 UTC 2026"
    assert_text_preserves_bytes(
        changelog.last_batch()[0].text,
        tests.bytes_literal("\xb3\xb7\xd8\xd9"),
    )
