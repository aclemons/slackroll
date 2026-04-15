import pytest
from slackroll import (
    SlackrollError,
    SlackwarePackage,
    download_verify,
    gnupg_exec_name,
    import_key,
    install_with_installpkg,
    remove_pkg,
    remove_pkgs,
    replace_pkg,
    upgrade_or_install,
    verify_signature,
    yield_gnupg_exec_name,
)

import tests

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import List, Tuple


def repo_pkg():
    # type: () -> SlackwarePackage
    return SlackwarePackage(
        "sbopkg",
        "0.38.2",
        "noarch",
        "1_wsr",
        "./packages",
        ".tgz",
        None,
        "https://repo.example.invalid/15.0/",
    )


def test_download_verify_downloads_official_pkg_and_signature(request):
    # type: (pytest.FixtureRequest) -> None
    pkg = tests.build_pkg("vim", "9.1", "./slackware64/ap")
    downloads = []  # type: List[Tuple[str, str, str]]
    removals = []  # type: List[str]
    renames = []  # type: List[Tuple[str, str]]

    def fake_download(base, name, dest):
        # type: (str, str, str) -> None
        downloads.append((base, name, dest))

    def fake_remove(path):
        # type: (str) -> None
        removals.append(path)

    def fake_rename(src, dst):
        # type: (str, str) -> None
        renames.append((src, dst))

    tests.start_patch(
        request, "slackroll.get_primary_mirror", lambda: "https://primary.example/"
    )
    tests.start_patch(request, "slackroll.get_temp_dir", lambda: "/tmp/slackroll")
    tests.start_patch(
        request, "slackroll.slackroll_pkgs_dir", "/var/cache/slackroll/packages"
    )
    tests.start_patch(request, "slackroll.download", fake_download)
    tests.start_patch(request, "slackroll.verify_signature", lambda filename: None)
    tests.start_patch(request, "slackroll.try_to_remove", fake_remove)
    tests.start_patch(request, "slackroll.try_to_rename", fake_rename)

    result = download_verify("https://mirror.example/", pkg)

    assert downloads == [
        ("https://primary.example/", pkg.fullsigname, "/tmp/slackroll"),
        ("https://mirror.example/", pkg.fullname, "/tmp/slackroll"),
    ]
    assert removals == ["/tmp/slackroll/%s" % pkg.signame]
    assert renames == [
        (
            "/tmp/slackroll/%s" % pkg.archivename,
            "/var/cache/slackroll/packages/%s" % pkg.archivename,
        )
    ]
    assert result == "/var/cache/slackroll/packages/%s" % pkg.archivename


def test_download_verify_uses_repo_url_and_cleans_up_on_failure(request):
    # type: (pytest.FixtureRequest) -> None
    pkg = repo_pkg()
    downloads = []  # type: List[Tuple[str, str, str]]
    removals = []  # type: List[str]
    renames = []  # type: List[Tuple[str, str]]

    def fake_download(base, name, dest):
        # type: (str, str, str) -> None
        downloads.append((base, name, dest))

    def raise_bad_sig(_filename):
        # type: (str) -> None
        raise SlackrollError("bad sig")

    def fake_remove(path):
        # type: (str) -> None
        removals.append(path)

    def fake_rename(src, dst):
        # type: (str, str) -> None
        renames.append((src, dst))

    tests.start_patch(
        request, "slackroll.get_primary_mirror", lambda: "https://primary.example/"
    )
    tests.start_patch(request, "slackroll.get_temp_dir", lambda: "/tmp/slackroll")
    tests.start_patch(
        request, "slackroll.slackroll_pkgs_dir", "/var/cache/slackroll/packages"
    )
    tests.start_patch(request, "slackroll.download", fake_download)
    tests.start_patch(request, "slackroll.verify_signature", raise_bad_sig)
    tests.start_patch(request, "slackroll.try_to_remove", fake_remove)
    tests.start_patch(request, "slackroll.try_to_rename", fake_rename)

    result = download_verify("https://mirror.example/", pkg)

    assert downloads == [
        (pkg.base_url("https://primary.example/"), pkg.fullsigname, "/tmp/slackroll"),
        (pkg.base_url("https://mirror.example/"), pkg.fullname, "/tmp/slackroll"),
    ]
    assert removals == [
        "/tmp/slackroll/%s" % pkg.signame,
        "/tmp/slackroll/%s" % pkg.archivename,
    ]
    assert renames == []
    assert result is None


def test_upgrade_or_install_passes_reinstall_flag(request):
    # type: (pytest.FixtureRequest) -> None
    fake_stdout = tests.FakeStream()
    calls = []  # type: List[List[str]]

    def fake_call(args):
        # type: (List[str]) -> int
        calls.append(args)
        return 0

    tests.start_patch(request, "slackroll.sys.stdout", fake_stdout)
    tests.start_patch(request, "slackroll.subprocess.call", fake_call)

    upgrade_or_install("/tmp/slackroll/vim-9.1-x86_64-1.txz", True)

    assert calls == [
        [
            "/sbin/upgradepkg",
            "--install-new",
            "--reinstall",
            "/tmp/slackroll/vim-9.1-x86_64-1.txz",
        ]
    ]
    assert fake_stdout.getvalue() == "Installing vim-9.1-x86_64-1.txz ...\n"


def test_remove_pkgs_runs_removepkg_and_dotnew_cleanup(request):
    # type: (pytest.FixtureRequest) -> None
    pkg1 = tests.build_pkg("vim", "9.1", "/var/log/packages")
    pkg2 = tests.build_pkg("git", "2.46.0", "/var/log/packages")
    seen = []  # type: List[str]
    cleaned = []  # type: List[List[str]]

    tests.start_patch(
        request,
        "slackroll.extract_dotnew_files",
        lambda pkg_list: ["/etc/rc.d/rc.vim.new"],
    )
    tests.start_patch(
        request,
        "slackroll.remove_pkg",
        lambda removepkg_arg: seen.append(removepkg_arg),
    )
    tests.start_patch(
        request,
        "slackroll.handle_dotnew_files_removal",
        lambda dotnew_files: cleaned.append(dotnew_files),
    )

    remove_pkgs([pkg1, pkg2])

    assert seen == [pkg1.idname, pkg2.idname]
    assert cleaned == [["/etc/rc.d/rc.vim.new"]]


def test_gnupg_exec_name_caches_first_successful_binary(request):
    # type: (pytest.FixtureRequest) -> None
    calls = []  # type: List[str]

    def fake_call(args, stdout=None, stderr=None):
        # type: (List[str], object, object) -> int
        calls.append(args[0])
        return {"gpg2": 1, "gpg": 0}[args[0]]

    tests.start_patch(request, "slackroll.gnupg_exec_name_cached", None)
    tests.start_patch(request, "slackroll.subprocess.call", fake_call)

    assert gnupg_exec_name() == "gpg"
    assert gnupg_exec_name() == "gpg"
    assert calls == ["gpg2", "gpg"]


def test_yield_gnupg_exec_name_skips_oserror_and_uses_first_working_binary(request):
    # type: (pytest.FixtureRequest) -> None
    calls = []  # type: List[str]

    def fake_call(args, stdout=None, stderr=None):
        # type: (List[str], object, object) -> int
        calls.append(args[0])
        if args[0] == "gpg2":
            raise OSError("missing")
        return 0

    tests.start_patch(request, "slackroll.subprocess.call", fake_call)

    generator = yield_gnupg_exec_name()

    if tests.PY2:
        assert generator.next() == "gpg"
    else:
        assert next(generator) == "gpg"
    assert calls == ["gpg2", "gpg"]


def test_import_key_exits_when_gnupg_returns_error(request):
    # type: (pytest.FixtureRequest) -> None
    fake_stdout = tests.FakeStream()
    exit_mock = tests.start_patch(request, "sys.exit")
    exit_mock.side_effect = ValueError("boom")
    tests.start_patch(request, "slackroll.sys.stdout", fake_stdout)
    tests.start_patch(request, "slackroll.gnupg_exec_name", lambda: "gpg")
    tests.start_patch(
        request, "slackroll.subprocess.call", lambda args, stdout=None, stderr=None: 1
    )

    pytest.raises(ValueError, import_key, "/tmp/key.asc")

    assert fake_stdout.getvalue() == "Importing keys from /tmp/key.asc ...\n"
    exit_mock.assert_called_with("ERROR: GnuPG exited with error when importing key")


def test_verify_signature_raises_on_nonzero_status(request):
    # type: (pytest.FixtureRequest) -> None
    fake_stdout = tests.FakeStream()
    fake_stderr = tests.FakeStream()

    tests.start_patch(request, "slackroll.sys.stdout", fake_stdout)
    tests.start_patch(request, "slackroll.sys.stderr", fake_stderr)
    tests.start_patch(request, "slackroll.gnupg_exec_name", lambda: "gpg")
    tests.start_patch(
        request, "slackroll.subprocess.call", lambda args, stdout=None, stderr=None: 2
    )

    err = pytest.raises(
        SlackrollError, verify_signature, "/tmp/slackroll/vim-9.1-x86_64-1.txz.asc"
    )

    assert str(err.value) == "GnuPG exited with status code 2"
    assert (
        fake_stdout.getvalue() == "Verifying signature vim-9.1-x86_64-1.txz.asc ... \n"
    )
    assert fake_stderr.getvalue() == (
        "ERROR: signature verification failed: /tmp/slackroll/vim-9.1-x86_64-1.txz.asc\n"
    )


def test_verify_signature_raises_when_subprocess_errors(request):
    # type: (pytest.FixtureRequest) -> None
    fake_stdout = tests.FakeStream()
    fake_stderr = tests.FakeStream()

    def raise_oserror(_args, stdout=None, stderr=None):
        # type: (List[str], object, object) -> int
        raise OSError("no gpg")

    tests.start_patch(request, "slackroll.sys.stdout", fake_stdout)
    tests.start_patch(request, "slackroll.sys.stderr", fake_stderr)
    tests.start_patch(request, "slackroll.gnupg_exec_name", lambda: "gpg")
    tests.start_patch(request, "slackroll.subprocess.call", raise_oserror)

    err = pytest.raises(SlackrollError, verify_signature, "/tmp/pkg.asc")

    assert str(err.value) == "no gpg"
    assert fake_stdout.getvalue() == "Verifying signature pkg.asc ... \n"
    assert fake_stderr.getvalue() == "ERROR: no gpg\n"


def test_install_with_installpkg_exits_on_failure(request):
    # type: (pytest.FixtureRequest) -> None
    fake_stdout = tests.FakeStream()
    exit_mock = tests.start_patch(request, "sys.exit")
    exit_mock.side_effect = ValueError("boom")
    tests.start_patch(request, "slackroll.sys.stdout", fake_stdout)
    tests.start_patch(request, "slackroll.subprocess.call", lambda args: 1)

    pytest.raises(ValueError, install_with_installpkg, "/tmp/pkg.txz")

    assert fake_stdout.getvalue() == "Installing pkg.txz ...\n"
    exit_mock.assert_called_with("ERROR: installation failed: /tmp/pkg.txz")


def test_replace_pkg_exits_on_failure(request):
    # type: (pytest.FixtureRequest) -> None
    fake_stdout = tests.FakeStream()
    exit_mock = tests.start_patch(request, "sys.exit")
    exit_mock.side_effect = ValueError("boom")
    calls = []  # type: List[List[str]]

    def fake_call(args):
        # type: (List[str]) -> int
        calls.append(args)
        return 1

    tests.start_patch(request, "slackroll.sys.stdout", fake_stdout)
    tests.start_patch(request, "slackroll.subprocess.call", fake_call)

    pytest.raises(ValueError, replace_pkg, "/installed/pkg.txz", "/tmp/newpkg.txz")

    assert calls == [["/sbin/upgradepkg", "/installed/pkg.txz%/tmp/newpkg.txz"]]
    assert fake_stdout.getvalue() == "Installing newpkg.txz ...\n"
    exit_mock.assert_called_with("ERROR: installation failed: /tmp/newpkg.txz")


def test_remove_pkg_exits_on_failure(request):
    # type: (pytest.FixtureRequest) -> None
    fake_stdout = tests.FakeStream()
    exit_mock = tests.start_patch(request, "sys.exit")
    exit_mock.side_effect = ValueError("boom")
    tests.start_patch(request, "slackroll.sys.stdout", fake_stdout)
    tests.start_patch(request, "slackroll.subprocess.call", lambda args: 1)

    pytest.raises(ValueError, remove_pkg, "vim-9.1-x86_64-1")

    assert fake_stdout.getvalue() == "Removing vim-9.1-x86_64-1 ...\n"
    exit_mock.assert_called_with("ERROR: removal failed: vim-9.1-x86_64-1")
