import pytest
from slackroll import (
    get_local_list,
    get_local_pkgs,
    get_normalized_known_files,
    get_pkg_filelists,
)

import tests

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Dict, List, Set


def test_get_pkg_filelists_rebuilds_and_returns_cached_map(request):
    # type: (pytest.FixtureRequest) -> None
    stored = {}  # type: Dict[str, List[str]]
    filenames = ["/pkgs/a", "/pkgs/b"]
    extracted = {
        "/pkgs/a": ["/usr/bin/a"],
        "/pkgs/b": ["/usr/bin/b", "/etc/b.conf"],
    }

    def fake_dump(contents, _filename):
        # type: (Dict[str, List[str]], str) -> None
        stored.clear()
        stored.update(contents)

    tests.start_patch(
        request, "slackroll.slackroll_local_pkgs_dir", "/pkgs", create=True
    )
    tests.start_patch(
        request, "slackroll.slackroll_local_pkgs_glob", "/pkgs/*", create=True
    )
    tests.start_patch(request, "slackroll.newer_than", lambda _left, _right: True)
    tests.start_patch(request, "slackroll.glob.glob", lambda _glob: filenames)
    tests.start_patch(
        request, "slackroll.extract_file_list", lambda filename: extracted[filename]
    )
    tests.start_patch(request, "slackroll.try_dump", fake_dump)
    tests.start_patch(request, "slackroll.try_load", lambda _filename: dict(stored))

    assert get_pkg_filelists() == extracted


def test_get_normalized_known_files_rebuilds_with_realpaths(request):
    # type: (pytest.FixtureRequest) -> None
    stored = set()  # type: Set[str]
    extracted = {
        "/pkgs/a": ["/usr/bin/a", "/usr/bin/link-a"],
        "/pkgs/b": ["/etc/b.conf"],
    }

    def fake_dump(contents, _filename):
        # type: (Set[str], str) -> None
        stored.clear()
        stored.update(contents)

    tests.start_patch(
        request, "slackroll.slackroll_local_pkgs_dir", "/pkgs", create=True
    )
    tests.start_patch(
        request, "slackroll.slackroll_local_pkgs_glob", "/pkgs/*", create=True
    )
    tests.start_patch(request, "slackroll.newer_than", lambda _left, _right: True)
    tests.start_patch(
        request, "slackroll.glob.glob", lambda _glob: ["/pkgs/a", "/pkgs/b"]
    )
    tests.start_patch(
        request, "slackroll.extract_file_list", lambda filename: extracted[filename]
    )
    tests.start_patch(
        request,
        "slackroll.os.path.realpath",
        lambda path: path.replace("link-a", "a"),
    )
    tests.start_patch(request, "slackroll.try_dump", fake_dump)
    tests.start_patch(request, "slackroll.try_load", lambda _filename: list(stored))

    assert sorted(get_normalized_known_files()) == ["/etc/b.conf", "/usr/bin/a"]


def test_get_local_pkgs_exits_when_no_local_packages_exist(request):
    # type: (pytest.FixtureRequest) -> None
    exit_mock = tests.start_patch(request, "sys.exit")
    exit_mock.side_effect = ValueError("boom")
    tests.start_patch(
        request,
        "slackroll.slackroll_local_pkgs_glob",
        "/var/log/packages/*",
        create=True,
    )
    tests.start_patch(request, "slackroll.glob.glob", lambda _glob: [])

    pytest.raises(ValueError, get_local_pkgs)

    exit_mock.assert_called_with("ERROR: could not read list of local packages")


def test_get_local_pkgs_parses_matching_packages(request):
    # type: (pytest.FixtureRequest) -> None
    filenames = [
        "/var/log/packages/vim-1.0-x86_64-1",
        "/var/log/packages/bash-5.2.037-x86_64-1",
    ]
    tests.start_patch(
        request,
        "slackroll.slackroll_local_pkgs_glob",
        "/var/log/packages/*",
        create=True,
    )
    tests.start_patch(request, "slackroll.glob.glob", lambda _glob: filenames)

    packages = get_local_pkgs()

    assert [pkg.archivename for pkg in packages] == [
        "vim-1.0-x86_64-1",
        "bash-5.2.037-x86_64-1",
    ]


def test_get_local_list_rebuilds_and_warns_for_duplicates(request):
    # type: (pytest.FixtureRequest) -> None
    fake_stdout = tests.FakeStream()
    stored = {}  # type: Dict[str, List[object]]
    local_pkgs = [
        tests.build_pkg("vim", "1.0", "/var/log/packages"),
        tests.build_pkg("vim", "2.0", "/var/log/packages"),
        tests.build_pkg("bash", "5.2.037", "/var/log/packages"),
    ]
    print_seq_mock = tests.start_patch(request, "slackroll.print_seq")

    def fake_dump(contents, _filename):
        # type: (Dict[str, List[object]], str) -> None
        stored.clear()
        stored.update(contents)

    tests.start_patch(request, "slackroll.sys.stdout", fake_stdout)
    tests.start_patch(
        request,
        "slackroll.slackroll_local_pkgs_dir",
        "/var/log/packages",
        create=True,
    )
    tests.start_patch(request, "slackroll.newer_than", lambda _left, _right: False)
    tests.start_patch(request, "slackroll.get_local_pkgs", lambda: list(local_pkgs))
    tests.start_patch(request, "slackroll.try_dump", fake_dump)
    tests.start_patch(request, "slackroll.try_load", lambda _filename: dict(stored))

    result = get_local_list(True)

    assert sorted(result.keys()) == ["bash", "vim"]
    assert [pkg.archivename for pkg in result["vim"]] == [
        "vim-1.0-x86_64-1.txz",
        "vim-2.0-x86_64-1.txz",
    ]
    assert fake_stdout.getvalue() == (
        "Rebuilding local package list...\n"
        "WARNING: packages with two or more local versions should be frozen or foreign\n"
    )
    print_seq_mock.assert_called_with(
        set(["vim"]), "WARNING: list of packages with two or more local versions:"
    )
