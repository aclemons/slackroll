import os
import shutil
from tempfile import mkdtemp

import pytest
from slackroll import (
    SlackwarePackage,
    decode_local_filelist_path,
    extend_manifest_list,
    extract_file_list,
    get_remote_info,
    get_remote_pkgs,
    local_info_header_from_text,
    manifest_database_from_text,
    read_lossless_text,
    slackroll_local_pkg_filelist_marker,
    texts_to_printed_bytes,
)

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
    from typing import Generator, List, Optional, Tuple, TypeVar, cast

    T = TypeVar("T")
else:

    def cast(_type, value):
        # type: (object, T) -> T
        return value


if tests.PY2:
    non_utf8_latin1 = "\xb3\xb7\xd8\xd9"
else:
    non_utf8_latin1 = b"\xb3\xb7\xd8\xd9".decode("latin-1")


@pytest.fixture  # type: ignore
def temp_dir():
    # type: () -> Generator[str, None, None]
    dir = mkdtemp()

    yield dir

    shutil.rmtree(dir)


def assert_text_preserves_bytes(text, expected_bytes):
    # type: (str, bytes) -> None
    if tests.PY2:
        assert expected_bytes in text
        return

    assert expected_bytes in text.encode("latin-1")


class FakePackage(object):
    def __init__(self, fullname):
        # type: (str) -> None
        self.fullname = fullname

    def base_url(self, mirror):
        # type: (str) -> str
        return mirror


def test_read_lossless_text_preserves_non_utf8_bytes(temp_dir):
    # type: (str) -> None
    filename = os.path.join(temp_dir, "example.txt")
    payload = b"Thanks to contributor \xb3\xb7\xd8\xd9 for the report.\n"

    handle = open(filename, "wb")
    try:
        handle.write(payload)
    finally:
        handle.close()

    text = read_lossless_text(filename)

    assert_text_preserves_bytes(text, b"\xb3\xb7\xd8\xd9")


def test_get_remote_info_preserves_non_utf8_bytes(temp_dir):
    # type: (str) -> None
    payload = b"PACKAGE NAME: example\nPACKAGE LOCATION: ./patches\nURL: https://example.\xb3\xb7\xd8\xd9/\n"
    package = cast(SlackwarePackage, FakePackage("example-1.0-noarch-1.txz"))

    def fake_download_or_exit(_mirror, filename, destination):
        # type: (str, str, str) -> None
        local_filename = os.path.join(destination, os.path.basename(filename))
        handle = open(local_filename, "wb")
        try:
            handle.write(payload)
        finally:
            handle.close()

    with patch("slackroll.slackroll_base_dir", temp_dir):
        with patch("slackroll.download_or_exit", fake_download_or_exit):
            info_text = get_remote_info("https://example.invalid/", package)

    assert_text_preserves_bytes(info_text, b"\xb3\xb7\xd8\xd9")


def test_local_info_header_from_text_preserves_non_utf8_bytes():
    # type: () -> None
    text = ("PACKAGE NAME: example\nURL: https://example.%s/\n%s/usr/doc/example\n") % (
        non_utf8_latin1,
        slackroll_local_pkg_filelist_marker,
    )

    header = local_info_header_from_text(text)

    assert (
        header == "PACKAGE NAME: example\nURL: https://example.%s/\n" % non_utf8_latin1
    )
    if not tests.PY2:
        assert b"\xb3\xb7\xd8\xd9" in header.encode("latin-1")


def test_texts_to_printed_bytes_preserves_non_utf8_bytes():
    # type: () -> None
    output = texts_to_printed_bytes(
        [
            "URL: https://example.%s/" % non_utf8_latin1,
            "Second line",
        ]
    )

    assert output.endswith(b"Second line\n")
    assert b"\xb3\xb7\xd8\xd9" in output


def test_texts_to_printed_bytes_single_text_matches_help_output():
    # type: () -> None
    output = texts_to_printed_bytes(["Help topic: %s" % non_utf8_latin1])

    assert output.endswith(b"\n")
    assert b"\xb3\xb7\xd8\xd9" in output


def test_decode_local_filelist_path_decodes_escapes_losslessly():
    # type: () -> None
    decoded = decode_local_filelist_path(
        "usr\\040share/doc/example-%s" % non_utf8_latin1
    )

    assert decoded == "usr share/doc/example-%s" % non_utf8_latin1
    if not tests.PY2:
        assert b"\xb3\xb7\xd8\xd9" in decoded.encode("latin-1")


def test_extract_file_list_preserves_non_utf8_bytes_and_escapes(temp_dir):
    # type: (str) -> None
    filename = os.path.join(temp_dir, "local-info.txt")
    payload = (
        b"PACKAGE NAME: example\n"
        b"FILE LIST:\n"
        b"usr\\040share/doc/example-\xb3\xb7\xd8\xd9\n"
        b"usr/bin/example\n"
    )

    handle = open(filename, "wb")
    try:
        handle.write(payload)
    finally:
        handle.close()

    paths = extract_file_list(filename)

    assert paths[0] == "/usr share/doc/example-%s" % non_utf8_latin1
    assert paths[1] == "/usr/bin/example"
    if not tests.PY2:
        assert b"\xb3\xb7\xd8\xd9" in paths[0].encode("latin-1")


def test_get_remote_pkgs_preserves_non_utf8_bytes(temp_dir):
    # type: (str) -> None
    filename = os.path.join(temp_dir, "FILELIST.TXT")
    payload = (
        b"-rw-r--r-- 1 root root 123 Jan 01 00:00 ./patches/packages/example-\xb3\xb7\xd8\xd9-1.0-noarch-1.txz\n"
        b"-rw-r--r-- 1 root root 456 Jan 01 00:00 ./slackware64/ap/bash-5.2.037-x86_64-1.txz\n"
    )

    handle = open(filename, "wb")
    try:
        handle.write(payload)
    finally:
        handle.close()

    packages = get_remote_pkgs(filename, "https://example.invalid/")

    assert (
        packages[0].fullname
        == "./patches/packages/example-%s-1.0-noarch-1.txz" % non_utf8_latin1
    )
    assert packages[1].fullname == "./slackware64/ap/bash-5.2.037-x86_64-1.txz"
    if not tests.PY2:
        assert b"\xb3\xb7\xd8\xd9" in packages[0].fullname.encode("latin-1")


def test_extend_manifest_list_reads_filelist_losslessly(temp_dir):
    # type: (str) -> None
    filename = os.path.join(temp_dir, "FILELIST.TXT")
    payload = (
        b"-rw-r--r-- 1 root root 123 Jan 01 00:00 ./patches/MANIFEST.bz2\n"
        b"-rw-r--r-- 1 root root 456 Jan 01 00:00 ./extra/MANIFEST.bz2\n"
    )

    handle = open(filename, "wb")
    try:
        handle.write(payload)
    finally:
        handle.close()

    manifest_list = []  # type: List[Tuple[Optional[int], str, str]]
    extend_manifest_list(manifest_list, None, "https://example.invalid/", filename)

    assert manifest_list == [
        (None, "https://example.invalid/", "./patches/MANIFEST.bz2"),
        (None, "https://example.invalid/", "./extra/MANIFEST.bz2"),
    ]


def test_manifest_database_from_text_preserves_non_utf8_bytes():
    # type: () -> None
    contents = (
        b"++==========================\n"
        b"|| Package: ./patches/packages/example-\xb3\xb7\xd8\xd9-1.0-noarch-1.txz\n"
        b"++==========================\n"
        b"-rw-r--r-- root/root 12 2026-02-17 00:00 usr/doc/example-\xb3\xb7\xd8\xd9/README\n"
        b"-rw-r--r-- root/root 42 2026-02-17 00:00 usr/bin/example\n"
        b"\n"
    )

    manifestdb = manifest_database_from_text(contents)

    package_name = "example-%s-1.0-noarch-1.txz" % non_utf8_latin1
    assert manifestdb["/usr/bin/example"] == [package_name]
    assert manifestdb["/usr/doc/example-%s/README" % non_utf8_latin1] == [package_name]
    if not tests.PY2:
        assert b"\xb3\xb7\xd8\xd9" in list(manifestdb.keys())[0].encode(
            "latin-1"
        ) or b"\xb3\xb7\xd8\xd9" in list(manifestdb.keys())[1].encode("latin-1")


def test_manifest_database_from_text_ignores_source_packages():
    # type: () -> None
    contents = (
        b"++==========================\n"
        b"|| Package: ./source/ap/example.tar.gz\n"
        b"++==========================\n"
        b"-rw-r--r-- root/root 42 2026-02-17 00:00 source/ap/example/example.SlackBuild\n"
        b"\n"
    )

    assert manifest_database_from_text(contents) == {}
