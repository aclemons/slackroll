import pytest
from slackroll import (
    ChangeLog,
    ChangeLogEntry,
    SlackrollOutputInterceptor,
    changelog_entries_operation,
    changelog_entries_to_bytes,
    changelog_operation,
    full_changelog_operation,
    list_changelog_operation,
    lossless_text_to_bytes,
    write_raw_output,
)

import tests

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False

if TYPE_CHECKING:
    pass


if tests.PY2:
    non_utf8_latin1 = "\xb3\xb7\xd8\xd9"
else:
    non_utf8_latin1 = tests.decode_bytes_literal("\xb3\xb7\xd8\xd9", "latin-1")


def test_changelog_entries_to_bytes_preserves_non_utf8_bytes():
    # type: () -> None
    entry = ChangeLogEntry(
        "Tue Feb 17 00:00:00 UTC 2026",
        "  Thanks to contributor %s for the report.\n" % non_utf8_latin1,
    )

    output = changelog_entries_to_bytes([entry])

    assert tests.bytes_literal("\xb3\xb7\xd8\xd9") in output


def test_write_raw_output_writes_bytes_to_stdout(request):
    # type: (pytest.FixtureRequest) -> None
    fake_stdout = tests.FakeStdout()
    payload = tests.bytes_literal("raw bytes \xb3\xb7\xd8\xd9\n")

    tests.start_patch(request, "slackroll.sys.stdout", fake_stdout)
    tests.start_patch(request, "slackroll.needs_pager", lambda _lines: False)
    write_raw_output(payload)

    if tests.PY2:
        assert fake_stdout.output == [payload]
    else:
        assert fake_stdout.buffer.output == [payload]


def test_write_raw_output_writes_bytes_to_pager(request):
    # type: (pytest.FixtureRequest) -> None
    pager = tests.FakePager()
    payload = tests.bytes_literal("raw bytes \xb3\xb7\xd8\xd9\n")

    tests.start_patch(request, "slackroll.needs_pager", lambda _lines: True)
    tests.start_patch(request, "slackroll.call_pager", lambda: pager)
    write_raw_output(payload)

    assert pager.stdin.output == [payload]


def test_lossless_text_to_bytes_handles_unicode_input():
    # type: () -> None
    payload = tests.decode_bytes_literal("raw bytes \xb3\xb7\xd8\xd9\n", "latin-1")

    assert lossless_text_to_bytes(payload) == tests.bytes_literal(
        "raw bytes \xb3\xb7\xd8\xd9\n"
    )


def test_output_interceptor_writes_bytes_to_pager(request):
    # type: (pytest.FixtureRequest) -> None
    pager = tests.FakePager()
    fake_stdout = tests.FakeTtyStdout()

    tests.start_patch(request, "slackroll.sys.stdout", fake_stdout)
    tests.start_patch(request, "slackroll.needs_pager", lambda _lines: True)
    tests.start_patch(request, "slackroll.call_pager", lambda: pager)
    interceptor = SlackrollOutputInterceptor()
    print("intercepted %s" % non_utf8_latin1)
    interceptor.stop()

    assert pager.stdin.output == [tests.bytes_literal("intercepted \xb3\xb7\xd8\xd9\n")]


def test_full_changelog_operation_writes_all_batches_in_reverse_order(request):
    # type: (pytest.FixtureRequest) -> None
    # Batch 0 is populated by the initial full download (no start_new_batch call).
    # Subsequent incremental updates call start_new_batch() then add_entries().
    cl = ChangeLog()
    cl.add_entry(
        ChangeLogEntry("Mon Jan 01 00:00:00 UTC 2024", "  first batch entry\n")
    )
    cl.start_new_batch()
    cl.add_entry(
        ChangeLogEntry("Tue Feb 01 00:00:00 UTC 2025", "  second batch entry\n")
    )

    pager = tests.FakePager()
    tests.start_patch(request, "slackroll.needs_pager", lambda _lines: True)
    tests.start_patch(request, "slackroll.call_pager", lambda: pager)

    full_changelog_operation(cl)

    output = tests.bytes_literal("").join(pager.stdin.output)
    # Most recent batch (batch 1) should appear before older batch (batch 0)
    pos_second = output.find(tests.bytes_literal("second batch entry"))
    pos_first = output.find(tests.bytes_literal("first batch entry"))
    assert pos_second != -1
    assert pos_first != -1
    assert pos_second < pos_first


def test_full_changelog_operation_empty_changelog_writes_empty_output(request):
    # type: (pytest.FixtureRequest) -> None
    cl = ChangeLog()

    fake_stdout = tests.FakeStdout()
    tests.start_patch(request, "slackroll.sys.stdout", fake_stdout)
    tests.start_patch(request, "slackroll.needs_pager", lambda _lines: False)

    full_changelog_operation(cl)

    combined = tests.bytes_literal("").join(
        fake_stdout.output if tests.PY2 else fake_stdout.buffer.output
    )
    assert combined == tests.bytes_literal("")


def test_changelog_operation_writes_last_batch_only(request):
    # type: (pytest.FixtureRequest) -> None
    cl = ChangeLog()
    cl.add_entry(ChangeLogEntry("Mon Jan 01 00:00:00 UTC 2024", "  old entry\n"))
    cl.start_new_batch()
    cl.add_entry(ChangeLogEntry("Tue Feb 01 00:00:00 UTC 2025", "  new entry\n"))

    pager = tests.FakePager()
    tests.start_patch(request, "slackroll.needs_pager", lambda _lines: True)
    tests.start_patch(request, "slackroll.call_pager", lambda: pager)

    changelog_operation(cl)

    output = tests.bytes_literal("").join(pager.stdin.output)
    assert tests.bytes_literal("new entry") in output
    assert tests.bytes_literal("old entry") not in output


def test_list_changelog_operation_lists_entries_newest_first(request):
    # type: (pytest.FixtureRequest) -> None
    cl = ChangeLog()
    cl.add_entry(ChangeLogEntry("Mon Jan 01 00:00:00 UTC 2024", "  old entry\n"))
    cl.start_new_batch()
    cl.add_entry(ChangeLogEntry("Tue Feb 01 00:00:00 UTC 2025", "  new entry\n"))

    fake_stdout = tests.FakeTtyStdout()
    pager = tests.FakePager()
    tests.start_patch(request, "slackroll.sys.stdout", fake_stdout)
    tests.start_patch(request, "slackroll.needs_pager", lambda _lines: True)
    tests.start_patch(request, "slackroll.call_pager", lambda: pager)

    list_changelog_operation(cl)

    output = tests.bytes_literal("").join(pager.stdin.output).decode("latin-1")
    pos_new = output.find("Tue Feb 01")
    pos_old = output.find("Mon Jan 01")
    assert pos_new != -1
    assert pos_old != -1
    assert pos_new < pos_old


def test_changelog_entries_operation_writes_selected_entries(request):
    # type: (pytest.FixtureRequest) -> None
    cl = ChangeLog()
    cl.add_entry(ChangeLogEntry("Mon Jan 01 00:00:00 UTC 2024", "  entry zero\n"))
    cl.start_new_batch()
    cl.add_entry(ChangeLogEntry("Tue Feb 01 00:00:00 UTC 2025", "  entry one\n"))

    pager = tests.FakePager()
    tests.start_patch(request, "slackroll.needs_pager", lambda _lines: True)
    tests.start_patch(request, "slackroll.call_pager", lambda: pager)

    changelog_entries_operation(cl, ["0.0"])

    output = tests.bytes_literal("").join(pager.stdin.output)
    assert tests.bytes_literal("entry zero") in output
    assert tests.bytes_literal("entry one") not in output


def test_changelog_entries_operation_exits_on_invalid_entry(request):
    # type: (pytest.FixtureRequest) -> None
    cl = ChangeLog()
    exit_mock = tests.start_patch(request, "sys.exit")
    exit_mock.side_effect = ValueError("boom")

    pytest.raises(ValueError, changelog_entries_operation, cl, ["99.99"])
