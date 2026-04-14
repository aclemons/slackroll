import pytest
from slackroll import (
    SlackwarePackage,
    extract_dotnew_files,
    handle_dotnew_files_both,
    handle_dotnew_files_installation,
    handle_dotnew_files_installation_batch,
    handle_dotnew_files_removal,
    old_file,
)

import tests

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Callable, List


def local_pkg(fullname):
    # type: (str) -> SlackwarePackage
    parts = fullname.rsplit("/", 1)
    path = parts[0]
    filename = parts[1]
    stem = filename[:-4]
    name, version, arch, build = stem.rsplit("-", 3)
    return SlackwarePackage(name, version, arch, build, path, ".txz", None, None)


def test_old_file_strips_new_suffix_only():
    # type: () -> None
    assert old_file("/etc/foo.conf.new") == "/etc/foo.conf"
    assert old_file("/etc/foo.conf") == "/etc/foo.conf"


def test_extract_dotnew_files_collects_unique_sorted_entries_and_optional_etc(request):
    # type: (pytest.FixtureRequest) -> None
    pkg_a = local_pkg("/var/log/packages/a-1.0-x86_64-1.txz")
    pkg_b = local_pkg("/var/log/packages/b-1.0-x86_64-1.txz")

    def fake_extract(filename):
        # type: (str) -> List[str]
        return {
            "/var/log/packages/a-1.0-x86_64-1.txz": [
                "/etc/a.new",
                "/etc/z.new",
                "/usr/bin/a",
            ],
            "/var/log/packages/b-1.0-x86_64-1.txz": ["/etc/a.new", "/etc/b.new"],
        }[filename]

    def fake_walk_append_if(_path, _predicate, output):
        # type: (str, Callable[[str], bool], List[str]) -> None
        output.append("/etc/c.new")

    tests.start_patch(request, "slackroll.extract_file_list", fake_extract)
    tests.start_patch(request, "slackroll.walk_append_if", fake_walk_append_if)

    assert list(extract_dotnew_files([pkg_a, pkg_b], False)) == [
        "/etc/a.new",
        "/etc/b.new",
        "/etc/z.new",
    ]
    assert list(extract_dotnew_files([pkg_a, pkg_b], True)) == [
        "/etc/a.new",
        "/etc/b.new",
        "/etc/c.new",
        "/etc/z.new",
    ]


def test_handle_dotnew_files_installation_dispatches_by_batch_mode(request):
    # type: (pytest.FixtureRequest) -> None
    batch_mock = tests.start_patch(
        request, "slackroll.handle_dotnew_files_installation_batch"
    )
    interactive_mock = tests.start_patch(
        request, "slackroll.handle_dotnew_files_installation_interactive"
    )

    tests.start_patch(request, "slackroll.slackroll_batch_mode", True)
    handle_dotnew_files_installation(["/etc/a.new"])
    batch_mock.assert_called_with(["/etc/a.new"])

    batch_mock.reset_mock()
    tests.start_patch(request, "slackroll.slackroll_batch_mode", False)
    handle_dotnew_files_installation(["/etc/b.new"])
    interactive_mock.assert_called_with(["/etc/b.new"])

    interactive_mock.reset_mock()
    handle_dotnew_files_installation([])
    assert interactive_mock.called is False
    assert batch_mock.called is False


def test_handle_dotnew_files_installation_batch_reports_all_existence_cases(request):
    # type: (pytest.FixtureRequest) -> None
    fake_stdout = tests.FakeStream()
    tests.start_patch(request, "slackroll.sys.stdout", fake_stdout)

    existing = {
        "/etc/both.new": True,
        "/etc/both": True,
        "/etc/new-only.new": True,
        "/etc/new-only": False,
        "/etc/old-only.new": False,
        "/etc/old-only": True,
        "/etc/neither.new": False,
        "/etc/neither": False,
    }
    tests.start_patch(request, "slackroll.os.path.exists", lambda path: existing[path])

    handle_dotnew_files_installation_batch(
        [
            "/etc/both.new",
            "/etc/new-only.new",
            "/etc/old-only.new",
            "/etc/neither.new",
        ]
    )

    assert fake_stdout.getvalue() == (
        "Keeping both /etc/both.new and /etc/both for manual review\n"
        "Renaming /etc/new-only.new to /etc/new-only because /etc/new-only does not exist\n"
        "Ignoring nonexistent /etc/old-only.new and keeping /etc/old-only\n"
        "WARNING: neither /etc/neither.new nor /etc/neither exist\n"
    )


def test_handle_dotnew_files_removal_returns_early_when_no_files_exist(request):
    # type: (pytest.FixtureRequest) -> None
    fake_stdout = tests.FakeStream()
    batch_mock = tests.start_patch(
        request, "slackroll.handle_dotnew_files_removal_batch"
    )
    interactive_mock = tests.start_patch(
        request, "slackroll.handle_dotnew_files_removal_interactive"
    )
    tests.start_patch(request, "slackroll.sys.stdout", fake_stdout)
    tests.start_patch(request, "slackroll.os.path.islink", lambda _path: False)
    tests.start_patch(request, "slackroll.os.path.exists", lambda _path: False)

    handle_dotnew_files_removal(["/etc/a.new"])

    assert fake_stdout.getvalue() == ""
    assert batch_mock.called is False
    assert interactive_mock.called is False


def test_handle_dotnew_files_removal_skips_files_still_owned_by_other_packages(request):
    # type: (pytest.FixtureRequest) -> None
    fake_stdout = tests.FakeStream()
    tests.start_patch(request, "slackroll.sys.stdout", fake_stdout)
    tests.start_patch(request, "slackroll.os.path.islink", lambda _path: False)
    tests.start_patch(request, "slackroll.os.path.exists", lambda _path: True)
    tests.start_patch(
        request,
        "slackroll.get_pkg_filelists",
        lambda: {"pkg": ["/etc/a.new", "/etc/a"]},
    )

    handle_dotnew_files_removal(["/etc/a.new"])

    assert fake_stdout.getvalue() == (
        "\nSome previous .new files have been found.\n"
        "Examining list in detail (this may take some seconds) ...\n"
        "All of them were present in other packages.\n"
    )


def test_handle_dotnew_files_removal_dispatches_remaining_files(request):
    # type: (pytest.FixtureRequest) -> None
    batch_mock = tests.start_patch(
        request, "slackroll.handle_dotnew_files_removal_batch"
    )
    interactive_mock = tests.start_patch(
        request, "slackroll.handle_dotnew_files_removal_interactive"
    )
    tests.start_patch(request, "slackroll.os.path.islink", lambda _path: False)
    tests.start_patch(request, "slackroll.os.path.exists", lambda _path: True)
    tests.start_patch(request, "slackroll.get_pkg_filelists", lambda: {})

    tests.start_patch(request, "slackroll.slackroll_batch_mode", True)
    handle_dotnew_files_removal(["/etc/a.new"])
    assert batch_mock.called is True
    assert set(batch_mock.call_args[0][0]) == set(["/etc/a.new", "/etc/a"])

    batch_mock.reset_mock()
    tests.start_patch(request, "slackroll.slackroll_batch_mode", False)
    handle_dotnew_files_removal(["/etc/b.new"])
    assert interactive_mock.called is True
    assert set(interactive_mock.call_args[0][0]) == set(["/etc/b.new", "/etc/b"])


def test_handle_dotnew_files_both_delegates_install_and_removal(request):
    # type: (pytest.FixtureRequest) -> None
    install_mock = tests.start_patch(
        request, "slackroll.handle_dotnew_files_installation"
    )
    removal_mock = tests.start_patch(request, "slackroll.handle_dotnew_files_removal")

    handle_dotnew_files_both(["/etc/a.new", "/etc/b.new"], ["/etc/b.new", "/etc/c.new"])

    install_mock.assert_called_with(["/etc/b.new", "/etc/c.new"])
    removal_mock.assert_called_with(["/etc/a.new"])
