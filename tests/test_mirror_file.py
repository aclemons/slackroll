import pytest
from slackroll import get_mirror_from_file

import tests

if tests.PY2:
    non_utf8_latin1 = "\xb3\xb7\xd8\xd9"
else:
    non_utf8_latin1 = tests.decode_bytes_literal("\xb3\xb7\xd8\xd9", "latin-1")


def test_get_mirror_from_file_adds_trailing_slash():
    # type: () -> None
    f = tests.named_temporary_file(delete=True)
    try:
        f.write(tests.bytes_literal("https://example.invalid\n"))
        f.flush()

        assert get_mirror_from_file(f.name) == "https://example.invalid/"
    finally:
        f.close()


def test_get_mirror_from_file_preserves_non_utf8_bytes():
    # type: () -> None
    f = tests.named_temporary_file(delete=True)
    try:
        f.write(tests.bytes_literal("https://example.\xb3\xb7\xd8\xd9\n"))
        f.flush()

        mirror = get_mirror_from_file(f.name)

        assert mirror == "https://example.%s/" % non_utf8_latin1
        if not tests.PY2:
            assert tests.bytes_literal("\xb3\xb7\xd8\xd9") in mirror.encode("latin-1")
    finally:
        f.close()


def test_get_mirror_from_file_rejects_multiple_lines():
    # type: () -> None
    f = tests.named_temporary_file(delete=True)
    try:
        f.write(
            tests.bytes_literal("https://example.invalid\nhttps://example2.invalid\n")
        )
        f.flush()

        pytest.raises(SystemExit, get_mirror_from_file, f.name)
    finally:
        f.close()
