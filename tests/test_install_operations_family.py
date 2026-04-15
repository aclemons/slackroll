import pytest
from slackroll import SlackrollBatchModeError, install_operations_family

import tests

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Dict, List, Sequence, Tuple

    from slackroll import SlackwarePackage


def test_install_operation_downloads_missing_packages_and_reviews_dotnew(request):
    # type: (pytest.FixtureRequest) -> None
    fake_stdout = tests.FakeStream()
    cached_pkg = tests.build_pkg("vim", "9.1", "./patches/packages")
    missing_pkg = tests.build_pkg("git", "2.46.0", "./patches/packages")
    local_vim = tests.build_pkg("vim", "9.0", "/var/log/packages")
    local_git = tests.build_pkg("git", "2.45.0", "/var/log/packages")
    installs = []  # type: List[Tuple[str, bool]]
    downloads = []  # type: List[str]
    dotnew_calls = []  # type: List[Sequence[str]]

    def fake_extract_dotnew_files(pkg_list, etc_too=False):
        # type: (Sequence[SlackwarePackage], bool) -> List[str]
        if etc_too:
            return ["/etc/vimrc.new"]
        return ["/etc/old-vimrc.new"]

    def fake_download_verify(mirror, pkg):
        # type: (str, SlackwarePackage) -> str
        downloads.append(pkg.archivename)
        return "/cache/%s" % pkg.archivename

    def fake_upgrade_or_install(filename, reinstall):
        # type: (str, bool) -> None
        installs.append((filename, reinstall))

    def fake_handle_dotnew_files_both(prev_dotnew, cur_dotnew):
        # type: (Sequence[str], Sequence[str]) -> None
        dotnew_calls.append(prev_dotnew)
        dotnew_calls.append(cur_dotnew)

    tests.start_patch(request, "slackroll.sys.stdout", fake_stdout)
    tests.start_patch(request, "slackroll.key_pkg_in", lambda _args: False)
    tests.start_patch(
        request, "slackroll.maybe_print_key_pkg_warning", lambda _persistent: False
    )
    tests.start_patch(
        request, "slackroll.get_mirror", lambda: "https://mirror.example/"
    )
    tests.start_patch(
        request,
        "slackroll.parse_install_args",
        lambda _args, _local, _remote, _use_local, _use_pasture, _filter_dupes: [
            cached_pkg,
            missing_pkg,
        ],
    )
    tests.start_patch(
        request, "slackroll.extract_dotnew_files", fake_extract_dotnew_files
    )
    tests.start_patch(
        request, "slackroll.optimum_size_conversion", lambda _size: "3.0k"
    )
    tests.start_patch(
        request, "slackroll.package_in_cache", lambda pkg: pkg == cached_pkg
    )
    tests.start_patch(
        request, "slackroll.enough_fs_resources", lambda _count, _size: True
    )
    tests.start_patch(request, "slackroll.download_verify", fake_download_verify)
    tests.start_patch(request, "slackroll.upgrade_or_install", fake_upgrade_or_install)
    tests.start_patch(
        request, "slackroll.handle_dotnew_files_both", fake_handle_dotnew_files_both
    )
    tests.start_patch(request, "slackroll.slackroll_pkgs_dir", "/cache")
    tests.start_patch(
        request,
        "slackroll.slackroll_local_pkgs_dir",
        "/var/log/packages",
        create=True,
    )

    install_operations_family(
        "install",
        ["vim", "git"],
        {"vim": [local_vim], "git": [local_git]},
        {"vim": [cached_pkg], "git": [missing_pkg]},
        {},
    )

    assert fake_stdout.getvalue() == (
        "Total size: 3.0k\nPackage vim-9.1-x86_64-1.txz found in cache\n"
    )
    assert downloads == ["git-2.46.0-x86_64-1.txz"]
    assert installs == [
        ("/cache/vim-9.1-x86_64-1.txz", False),
        ("/cache/git-2.46.0-x86_64-1.txz", False),
    ]
    assert dotnew_calls == [["/etc/old-vimrc.new"], ["/etc/vimrc.new"]]


def test_installpkg_uses_installpkg_and_installation_dotnew_handler(request):
    # type: (pytest.FixtureRequest) -> None
    fake_stdout = tests.FakeStream()
    pkg = tests.build_pkg("vim", "9.1", "./patches/packages")
    installs = []  # type: List[str]
    dotnew_calls = []  # type: List[Sequence[str]]

    def fake_extract_dotnew_files(_pkg_list, etc_too=False):
        # type: (Sequence[SlackwarePackage], bool) -> List[str]
        assert etc_too is True
        return ["/etc/vimrc.new"]

    tests.start_patch(request, "slackroll.sys.stdout", fake_stdout)
    tests.start_patch(request, "slackroll.key_pkg_in", lambda _args: False)
    tests.start_patch(
        request, "slackroll.maybe_print_key_pkg_warning", lambda _persistent: False
    )
    tests.start_patch(
        request, "slackroll.get_mirror", lambda: "https://mirror.example/"
    )
    tests.start_patch(
        request,
        "slackroll.parse_install_args",
        lambda _args, _local, _remote, _use_local, _use_pasture, _filter_dupes: [pkg],
    )
    tests.start_patch(
        request, "slackroll.optimum_size_conversion", lambda _size: "1.0k"
    )
    tests.start_patch(request, "slackroll.package_in_cache", lambda _pkg: True)
    tests.start_patch(
        request, "slackroll.enough_fs_resources", lambda _count, _size: True
    )
    tests.start_patch(
        request, "slackroll.extract_dotnew_files", fake_extract_dotnew_files
    )
    tests.start_patch(request, "slackroll.slackroll_pkgs_dir", "/cache")
    tests.start_patch(
        request,
        "slackroll.slackroll_local_pkgs_dir",
        "/var/log/packages",
        create=True,
    )
    tests.start_patch(
        request,
        "slackroll.install_with_installpkg",
        lambda filename: installs.append(filename),
    )
    tests.start_patch(
        request,
        "slackroll.handle_dotnew_files_installation",
        lambda dotnew_files: dotnew_calls.append(dotnew_files),
    )

    install_operations_family("installpkg", ["vim"], {}, {"vim": [pkg]}, {})

    assert fake_stdout.getvalue() == (
        "Total size: 1.0k\nPackage vim-9.1-x86_64-1.txz found in cache\n"
    )
    assert installs == ["/cache/vim-9.1-x86_64-1.txz"]
    assert dotnew_calls == [["/etc/vimrc.new"]]


def test_info_operation_reads_local_and_remote_info_in_order(request):
    # type: (pytest.FixtureRequest) -> None
    local_pkg = tests.build_pkg("vim", "9.1", "/var/log/packages")
    remote_pkg = tests.build_pkg("git", "2.46.0", "./patches/packages")
    written = []  # type: List[bytes]

    tests.start_patch(request, "slackroll.key_pkg_in", lambda _args: False)
    tests.start_patch(
        request, "slackroll.maybe_print_key_pkg_warning", lambda _persistent: False
    )
    tests.start_patch(
        request, "slackroll.get_mirror", lambda: "https://mirror.example/"
    )
    tests.start_patch(
        request,
        "slackroll.parse_install_args",
        lambda _args, _local, _remote, _use_local, _use_pasture, _filter_dupes: [
            local_pkg,
            remote_pkg,
        ],
    )
    tests.start_patch(
        request,
        "slackroll.read_lossless_text",
        lambda path: "header for %s\nFILE LIST:\n" % path,
    )
    tests.start_patch(
        request,
        "slackroll.local_info_header_from_text",
        lambda text: text.splitlines()[0],
    )
    tests.start_patch(
        request,
        "slackroll.get_remote_info",
        lambda _mirror, pkg: "remote info for %s" % pkg.name,
    )
    tests.start_patch(
        request,
        "slackroll.write_raw_output",
        lambda output: written.append(output),
    )

    install_operations_family(
        "info",
        ["vim", "git"],
        {"vim": [local_pkg]},
        {"git": [remote_pkg]},
        {},
    )

    assert written == [
        tests.bytes_literal(
            "header for /var/log/packages/vim-9.1-x86_64-1.txz\nremote info for git\n"
        )
    ]


def test_install_operation_aborts_in_batch_mode_when_space_is_low(request):
    # type: (pytest.FixtureRequest) -> None
    pkg = tests.build_pkg("vim", "9.1", "./patches/packages")
    warned = []  # type: List[bool]

    tests.start_patch(request, "slackroll.key_pkg_in", lambda _args: False)
    tests.start_patch(
        request, "slackroll.maybe_print_key_pkg_warning", lambda _persistent: False
    )
    tests.start_patch(
        request, "slackroll.get_mirror", lambda: "https://mirror.example/"
    )
    tests.start_patch(
        request,
        "slackroll.parse_install_args",
        lambda _args, _local, _remote, _use_local, _use_pasture, _filter_dupes: [pkg],
    )
    tests.start_patch(
        request, "slackroll.extract_dotnew_files", lambda _pkg_list, etc_too=False: []
    )
    tests.start_patch(
        request, "slackroll.optimum_size_conversion", lambda _size: "1.0k"
    )
    tests.start_patch(request, "slackroll.package_in_cache", lambda _pkg: False)
    tests.start_patch(
        request, "slackroll.enough_fs_resources", lambda _count, _size: False
    )
    tests.start_patch(
        request, "slackroll.low_fs_resources_warning", lambda: warned.append(True)
    )
    tests.start_patch(request, "slackroll.slackroll_batch_mode", True)

    err = pytest.raises(
        SlackrollBatchModeError,
        install_operations_family,
        "install",
        ["vim"],
        {},
        {"vim": [pkg]},
        {},
    )

    assert str(err.value) == "Aborting install in batch mode since fs space is low"
    assert warned == [True]
