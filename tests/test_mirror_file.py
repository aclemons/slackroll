from tempfile import NamedTemporaryFile

import pytest
from slackroll import get_mirror_from_file

import tests

if tests.PY2:
    non_utf8_tld = "\xb3\xb7\xd8\xd9"
else:
    non_utf8_tld = b"\xb3\xb7\xd8\xd9".decode("latin-1")


def test_get_mirror_from_file_adds_trailing_slash():
    # type: () -> None
    f = NamedTemporaryFile(delete=True)
    try:
        f.write(b"https://example.invalid\n")
        f.flush()

        assert get_mirror_from_file(f.name) == "https://example.invalid/"
    finally:
        f.close()


def test_get_mirror_from_file_preserves_non_utf8_bytes():
    # type: () -> None
    f = NamedTemporaryFile(delete=True)
    try:
        f.write(b"https://example.\xb3\xb7\xd8\xd9\n")
        f.flush()

        mirror = get_mirror_from_file(f.name)

        assert mirror == "https://example.%s/" % non_utf8_tld
        if not tests.PY2:
            assert b"\xb3\xb7\xd8\xd9" in mirror.encode("latin-1")
    finally:
        f.close()


def test_get_mirror_from_file_rejects_multiple_lines():
    # type: () -> None
    f = NamedTemporaryFile(delete=True)
    try:
        f.write(b"https://example.invalid\nhttps://example2.invalid\n")
        f.flush()

        with pytest.raises(SystemExit):
            get_mirror_from_file(f.name)
    finally:
        f.close()
