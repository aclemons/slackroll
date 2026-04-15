import bz2
import os
import shutil
from tempfile import mkdtemp

import pytest
from slackroll import update_manifest_database, update_operation

import tests

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Any, Dict, List, Optional, Tuple


@pytest.fixture  # type: ignore
def temp_dir(request):
    # type: (pytest.FixtureRequest) -> str
    dir = mkdtemp()

    def teardown():
        # type: () -> None
        shutil.rmtree(dir)

    request.addfinalizer(teardown)
    return dir


def test_update_operation_downloads_mirror_and_repositories(request, temp_dir):
    # type: (pytest.FixtureRequest, str) -> None
    download_calls = []  # type: List[Tuple[str, str, str, str]]
    remote_calls = []  # type: List[Tuple[str, Optional[str]]]
    manifest_calls = []  # type: List[Tuple[Optional[int], str, str]]
    removed = []  # type: List[str]
    dumped = {}  # type: Dict[str, Any]

    local_filelist = os.path.join(temp_dir, "FILELIST.TXT")
    legacy_filelist = os.path.join(temp_dir, "legacy-FILELIST.TXT")
    remotelist_file = os.path.join(temp_dir, "remotelist.db")
    manifestlist_file = os.path.join(temp_dir, "manifestlist.db")

    def fake_download_or_exit(base, filename, destination, displayed_name):
        # type: (str, str, str, str) -> None
        download_calls.append((base, filename, destination, displayed_name))

    def fake_extend_remote(local_path, remote_list, repo=None):
        # type: (str, Dict[str, List[str]], Optional[str]) -> None
        remote_calls.append((local_path, repo))
        key = repo or "mirror"
        value = remote_list.get(key, [])
        value.append(key)
        remote_list[key] = value

    def fake_extend_manifest(manifest_list, index, mirror, local_path):
        # type: (List[Tuple[Optional[int], str, str]], Optional[int], str, str) -> None
        manifest_calls.append((index, mirror, local_path))
        manifest_list.append(
            (index, mirror, "./MANIFEST-%s.bz2" % (index is None and "mirror" or index))
        )

    def fake_dump(contents, filename):
        # type: (Any, str) -> None
        dumped[filename] = contents

    def fake_exists(path):
        # type: (str) -> bool
        return path == legacy_filelist

    def fake_remove(path):
        # type: (str) -> None
        removed.append(path)

    tests.start_patch(request, "slackroll.get_temp_dir", lambda: temp_dir)
    tests.start_patch(
        request,
        "slackroll.get_repo_list",
        lambda: ["https://repo-one.example/", "https://repo-two.example/"],
    )
    tests.start_patch(request, "slackroll.download_or_exit", fake_download_or_exit)
    tests.start_patch(request, "slackroll.extend_remote_list", fake_extend_remote)
    tests.start_patch(request, "slackroll.extend_manifest_list", fake_extend_manifest)
    tests.start_patch(request, "slackroll.try_dump", fake_dump)
    tests.start_patch(request, "slackroll.try_to_remove", fake_remove)
    tests.start_patch(request, "slackroll.os.path.exists", fake_exists)
    tests.start_patch(request, "slackroll.slackroll_local_filelist", legacy_filelist)
    tests.start_patch(
        request, "slackroll.slackroll_remotelist_filename", remotelist_file
    )
    tests.start_patch(
        request, "slackroll.slackroll_manifest_list_filename", manifestlist_file
    )

    update_operation("https://mirror.example/")

    assert download_calls == [
        (
            "https://mirror.example/",
            "FILELIST.TXT",
            temp_dir,
            "FILELIST.TXT from mirror",
        ),
        (
            "https://repo-one.example/",
            "FILELIST.TXT",
            temp_dir,
            "FILELIST.TXT from repository 0",
        ),
        (
            "https://repo-two.example/",
            "FILELIST.TXT",
            temp_dir,
            "FILELIST.TXT from repository 1",
        ),
    ]
    assert remote_calls == [
        (local_filelist, None),
        (local_filelist, "https://repo-one.example/"),
        (local_filelist, "https://repo-two.example/"),
    ]
    assert manifest_calls == [
        (None, "https://mirror.example/", local_filelist),
        (0, "https://repo-one.example/", local_filelist),
        (1, "https://repo-two.example/", local_filelist),
    ]
    assert removed == [local_filelist, local_filelist, local_filelist, legacy_filelist]
    assert dumped[remotelist_file] == {
        "mirror": ["mirror"],
        "https://repo-one.example/": ["https://repo-one.example/"],
        "https://repo-two.example/": ["https://repo-two.example/"],
    }
    assert dumped[manifestlist_file] == [
        (None, "https://mirror.example/", "./MANIFEST-mirror.bz2"),
        (0, "https://repo-one.example/", "./MANIFEST-0.bz2"),
        (1, "https://repo-two.example/", "./MANIFEST-1.bz2"),
    ]


def test_update_manifest_database_merges_entries_and_removes_temp_files(
    request, temp_dir
):
    # type: (pytest.FixtureRequest, str) -> None
    manifestlist_file = os.path.join(temp_dir, "manifestlist.db")
    manifestdb_file = os.path.join(temp_dir, "manifest.db")
    output_name = os.path.join(temp_dir, "MANIFEST.bz2")
    removed = []  # type: List[str]
    downloads = []  # type: List[Tuple[str, str, str, str]]
    dumped = {}  # type: Dict[str, Dict[str, List[str]]]
    manifest_list = [
        (None, "https://mirror.example/", "./patches/MANIFEST.bz2"),
        (0, "https://repo.example/", "./extra/MANIFEST.bz2"),
    ]  # type: List[Tuple[Optional[int], str, str]]
    payloads = {
        "./patches/MANIFEST.bz2": (
            tests.bytes_literal("++==========================\n")
            + tests.bytes_literal(
                "|| Package: ./patches/packages/example-1.0-noarch-1.txz\n"
            )
            + tests.bytes_literal("++==========================\n")
            + tests.bytes_literal(
                "-rw-r--r-- root/root 42 2026-02-17 00:00 usr/bin/example\n"
            )
            + tests.bytes_literal("\n")
        ),
        "./extra/MANIFEST.bz2": (
            tests.bytes_literal("++==========================\n")
            + tests.bytes_literal(
                "|| Package: ./extra/example-addon-2.0-noarch-1.txz\n"
            )
            + tests.bytes_literal("++==========================\n")
            + tests.bytes_literal(
                "-rw-r--r-- root/root 42 2026-02-17 00:00 usr/bin/example\n"
            )
            + tests.bytes_literal(
                "-rw-r--r-- root/root 18 2026-02-17 00:00 etc/example-addon.conf\n"
            )
            + tests.bytes_literal("\n")
        ),
    }  # type: Dict[str, bytes]

    def fake_exists(path):
        # type: (str) -> bool
        return path == manifestlist_file

    def fake_download_or_exit(url, path, destination, displayed_name):
        # type: (str, str, str, str) -> None
        downloads.append((url, path, destination, displayed_name))
        stream = bz2.BZ2File(os.path.join(destination, "MANIFEST.bz2"), "w")
        try:
            stream.write(payloads[path])
        finally:
            stream.close()

    def fake_dump(contents, filename):
        # type: (Dict[str, List[str]], str) -> None
        dumped[filename] = contents

    def fake_remove(path):
        # type: (str) -> None
        removed.append(path)

    tests.start_patch(request, "slackroll.os.path.exists", fake_exists)
    tests.start_patch(
        request, "slackroll.try_load", lambda _filename: list(manifest_list)
    )
    tests.start_patch(request, "slackroll.get_temp_dir", lambda: temp_dir)
    tests.start_patch(request, "slackroll.download_or_exit", fake_download_or_exit)
    tests.start_patch(request, "slackroll.try_dump", fake_dump)
    tests.start_patch(request, "slackroll.try_to_remove", fake_remove)
    tests.start_patch(request, "slackroll.print_flush", lambda _text: None)
    tests.start_patch(
        request, "slackroll.slackroll_manifest_list_filename", manifestlist_file
    )
    tests.start_patch(request, "slackroll.slackroll_manifest_filename", manifestdb_file)

    update_manifest_database()

    assert downloads == [
        (
            "https://mirror.example/",
            "./patches/MANIFEST.bz2",
            temp_dir,
            "./patches/MANIFEST.bz2 from mirror",
        ),
        (
            "https://repo.example/",
            "./extra/MANIFEST.bz2",
            temp_dir,
            "./extra/MANIFEST.bz2 from repository 0",
        ),
    ]
    assert removed == [output_name, output_name]
    assert dumped[manifestdb_file] == {
        "/usr/bin/example": [
            "example-1.0-noarch-1.txz",
            "example-addon-2.0-noarch-1.txz",
        ],
        "/etc/example-addon.conf": ["example-addon-2.0-noarch-1.txz"],
    }


def test_update_manifest_database_exits_when_update_has_not_run(request, temp_dir):
    # type: (pytest.FixtureRequest, str) -> None
    manifestlist_file = os.path.join(temp_dir, "manifestlist.db")
    exit_mock = tests.start_patch(request, "sys.exit")
    exit_mock.side_effect = ValueError("boom")
    tests.start_patch(
        request, "slackroll.slackroll_manifest_list_filename", manifestlist_file
    )
    tests.start_patch(request, "slackroll.os.path.exists", lambda _path: False)

    pytest.raises(ValueError, update_manifest_database)

    exit_mock.assert_called_with(
        'ERROR: %s not found: run "update" first' % manifestlist_file
    )
