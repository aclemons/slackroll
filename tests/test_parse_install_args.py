import pytest
from slackroll import (
    SlackwarePackage,
    parse_install_args,
    parse_pkg_arg,
)

import tests

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Dict, List


def test_parse_pkg_arg_parses_full_archive_name():
    # type: () -> None
    is_full, name, pkg = parse_pkg_arg("./slackware64/ap/vim-1.0-x86_64-1.txz")

    assert is_full is True
    assert name == "vim"
    assert pkg is not None
    assert pkg.archivename == "vim-1.0-x86_64-1.txz"


def test_parse_install_args_prefers_local_pkg_for_info_full_version():
    # type: () -> None
    local_pkg = tests.build_pkg("vim", "1.0", "./local/ap")
    remote_pkg = tests.build_pkg("vim", "1.0", "./slackware64/ap")
    local_list = {"vim": [local_pkg]}  # type: Dict[str, List[SlackwarePackage]]
    remote_list = {"vim": [remote_pkg]}  # type: Dict[str, List[SlackwarePackage]]

    chosen = parse_install_args(
        ["./slackware64/ap/vim-1.0-x86_64-1.txz"],
        local_list,
        remote_list,
        True,
        True,
        True,
    )

    assert chosen == [local_pkg]


def test_parse_install_args_deduplicates_local_and_remote_info_candidates():
    # type: () -> None
    local_pkg = tests.build_pkg("vim", "1.0", "./slackware64/ap")
    local_list = {"vim": [local_pkg]}  # type: Dict[str, List[SlackwarePackage]]
    remote_list = {"vim": [tests.build_pkg("vim", "1.0", "./slackware64/ap")]}  # type: Dict[str, List[SlackwarePackage]]

    chosen = parse_install_args(["vim"], local_list, remote_list, True, True, True)

    assert chosen == [local_pkg]


def test_parse_install_args_warns_when_package_only_exists_in_pasture(request):
    # type: (pytest.FixtureRequest) -> None
    fake_stdout = tests.FakeStream()
    tests.start_patch(request, "slackroll.sys.stdout", fake_stdout)
    local_list = {}  # type: Dict[str, List[SlackwarePackage]]
    remote_list = {
        "vim": [tests.build_pkg("vim", "1.0", "./pasture/ap")],
    }  # type: Dict[str, List[SlackwarePackage]]

    chosen = parse_install_args(["vim"], local_list, remote_list, False, False, False)

    assert chosen == []
    assert fake_stdout.getvalue() == "WARNING: vim only present in /pasture/\n"


def test_parse_install_args_errors_for_missing_name_that_looks_like_full_version(
    request,
):
    # type: (pytest.FixtureRequest) -> None
    fake_stdout = tests.FakeStream()
    exit_mock = tests.start_patch(request, "sys.exit")
    tests.start_patch(request, "slackroll.sys.stdout", fake_stdout)
    exit_mock.side_effect = ValueError("boom")

    pytest.raises(
        ValueError,
        parse_install_args,
        ["vim-1.0-x86_64-1"],
        {},
        {},
        False,
        True,
        False,
    )

    assert (
        fake_stdout.getvalue()
        == 'WARNING: file extension may be missing on "vim-1.0-x86_64-1"\n'
    )
    exit_mock.assert_called_with("ERROR: no package named vim-1.0-x86_64-1")


def test_parse_install_args_uses_choose_pkg_for_multiple_candidates(request):
    # type: (pytest.FixtureRequest) -> None
    fake_stdout = tests.FakeStream()
    choose_pkg_mock = tests.start_patch(request, "slackroll.choose_pkg")
    tests.start_patch(request, "slackroll.sys.stdout", fake_stdout)
    local_pkg = tests.build_pkg("vim", "1.0", "./local/ap")
    remote_pkg_1 = tests.build_pkg("vim", "2.0", "./slackware64/ap")
    remote_pkg_2 = tests.build_pkg("vim", "3.0", "./patches/packages")
    choose_pkg_mock.return_value = remote_pkg_2

    chosen = parse_install_args(
        ["vim"],
        {"vim": [local_pkg]},
        {"vim": [remote_pkg_1, remote_pkg_2]},
        False,
        True,
        False,
    )

    assert chosen == [remote_pkg_2]
    assert fake_stdout.getvalue() == "Local: vim-1.0-x86_64-1.txz\n"
    choose_pkg_mock.assert_called_with([remote_pkg_1, remote_pkg_2])


def test_parse_install_args_errors_for_missing_remote_full_version(request):
    # type: (pytest.FixtureRequest) -> None
    exit_mock = tests.start_patch(request, "sys.exit")
    exit_mock.side_effect = ValueError("boom")

    pytest.raises(
        ValueError,
        parse_install_args,
        ["./slackware64/ap/vim-1.0-x86_64-1.txz"],
        {},
        {},
        False,
        True,
        False,
    )

    exit_mock.assert_called_with(
        "ERROR: unable to find remote package vim-1.0-x86_64-1.txz"
    )
