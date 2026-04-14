# -*- coding: utf-8 -*-

import re

from slackroll import SlackwarePackage, extend_remote_list

import tests

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Dict, List


if tests.PY2:
    multibyte_pkg_name = tests.bytes_literal(
        "ca-certificates-F\xc5\x91tan\xc3\xbas\xc3\xadtv\xc3\xa1ny"
    )
    multibyte_repo_url = tests.bytes_literal(
        "https://repo.example.invalid/F\xc5\x91tan\xc3\xbas\xc3\xadtv\xc3\xa1ny/"
    )
else:
    multibyte_pkg_name = tests.decode_bytes_literal(
        "ca-certificates-F\xc5\x91tan\xc3\xbas\xc3\xadtv\xc3\xa1ny",
        "latin-1",
    )
    multibyte_repo_url = tests.decode_bytes_literal(
        "https://repo.example.invalid/F\xc5\x91tan\xc3\xbas\xc3\xadtv\xc3\xa1ny/",
        "latin-1",
    )


def repo_pkg(name, version, path, url):
    # type: (str, str, str, str) -> SlackwarePackage
    return SlackwarePackage(name, version, "x86_64", "1", path, ".txz", None, url)


def test_extend_remote_list_skips_blacklisted_package(request):
    # type: (object) -> None
    remote_list = {}  # type: Dict[str, List[SlackwarePackage]]
    blacklisted = tests.build_pkg("blocked", "1.0", "./slackware64/ap")
    allowed = tests.build_pkg("vim", "1.0", "./slackware64/ap")
    tests.start_patch(
        request,
        "slackroll.get_blacklist_re",
        lambda: [(re.compile("blocked"), re.compile("mirror/blocked"))],
    )
    tests.start_patch(
        request,
        "slackroll.get_remote_pkgs",
        lambda _local_filelist, _pkgs_url: [blacklisted, allowed],
    )

    extend_remote_list("FILELIST.TXT", remote_list, "https://mirror/blocked/")

    assert remote_list == {"vim": [allowed]}


def test_extend_remote_list_skips_multibyte_blacklisted_package_and_url(request):
    # type: (object) -> None
    remote_list = {}  # type: Dict[str, List[SlackwarePackage]]
    blacklisted = repo_pkg(
        multibyte_pkg_name,
        "1.0",
        "./testing/packages",
        multibyte_repo_url,
    )
    allowed = tests.build_pkg("vim", "1.0", "./slackware64/ap")

    tests.start_patch(
        request,
        "slackroll.get_blacklist",
        lambda: ["Főtanúsítvány@https://repo.example.invalid/Főtanúsítvány/"],
    )
    tests.start_patch(
        request,
        "slackroll.get_remote_pkgs",
        lambda _local_filelist, _pkgs_url: [blacklisted, allowed],
    )

    extend_remote_list("FILELIST.TXT", remote_list, "https://mirror.example.invalid/")

    assert remote_list == {"vim": [allowed]}


def test_extend_remote_list_keeps_extra_and_patch_when_main_also_exists(request):
    # type: (object) -> None
    remote_list = {}  # type: Dict[str, List[SlackwarePackage]]
    main_pkg = tests.build_pkg("vim", "1.0", "./slackware64/ap")
    extra_pkg = tests.build_pkg("vim", "1.0", "./extra")
    patch_pkg = tests.build_pkg("vim", "2.0", "./patches/packages")
    tests.start_patch(request, "slackroll.get_blacklist_re", lambda: [])
    tests.start_patch(
        request,
        "slackroll.get_remote_pkgs",
        lambda _local_filelist, _pkgs_url: [main_pkg, extra_pkg, patch_pkg],
    )

    extend_remote_list("FILELIST.TXT", remote_list)

    assert remote_list == {"vim": [extra_pkg, patch_pkg]}


def test_extend_remote_list_keeps_patch_and_repo_versions_over_main(request):
    # type: (object) -> None
    remote_list = {}  # type: Dict[str, List[SlackwarePackage]]
    main_pkg = tests.build_pkg("vim", "1.0", "./slackware64/ap")
    repo_pkg_version = repo_pkg(
        "vim", "3.0", "./testing/packages", "https://repo.example.invalid/"
    )
    patch_pkg = tests.build_pkg("vim", "2.0", "./patches/packages")
    tests.start_patch(request, "slackroll.get_blacklist_re", lambda: [])
    tests.start_patch(
        request,
        "slackroll.get_remote_pkgs",
        lambda _local_filelist, _pkgs_url: [main_pkg, repo_pkg_version, patch_pkg],
    )

    extend_remote_list("FILELIST.TXT", remote_list, "https://mirror.example.invalid/")

    assert remote_list == {"vim": [repo_pkg_version, patch_pkg]}
    assert remote_list["vim"][0].url("https://mirror.example.invalid/") == (
        "https://repo.example.invalid/testing/packages/vim-3.0-x86_64-1.txz"
    )
