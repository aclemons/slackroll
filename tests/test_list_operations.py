# -*- coding: utf-8 -*-
import pytest
from slackroll import (
    list_transient_operation,
    list_upgrades_and_outdated_frozen_operation,
)

import tests

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Any, Dict, List

    from slackroll import SlackwarePackage

    from tests import PersistentList


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _local(pkgs):
    # type: (List[SlackwarePackage]) -> Dict[str, List[SlackwarePackage]]
    result = {}  # type: Dict[str, List[SlackwarePackage]]
    for p in pkgs:
        result.setdefault(p.name, []).append(p)
    return result


def _remote(pkgs):
    # type: (List[SlackwarePackage]) -> Dict[str, List[SlackwarePackage]]
    result = {}  # type: Dict[str, List[SlackwarePackage]]
    for p in pkgs:
        result.setdefault(p.name, []).append(p)
    return result


def _capture_stdout(request, fn, *args):
    # type: (pytest.FixtureRequest, object, *object) -> str
    fake_stdout = tests.FakeTtyStdout()
    tests.start_patch(request, "slackroll.sys.stdout", fake_stdout)
    tests.start_patch(request, "slackroll.needs_pager", lambda _: False)
    fn(*args)  # type: ignore
    if tests.PY2:
        return "".join(fake_stdout.output)
    return "".join(fake_stdout.output) + tests.bytes_literal("").join(
        fake_stdout.buffer.output
    ).decode("latin-1")


def _capture_list_transient(request, local_list, remote_list, persistent_list):
    # type: (pytest.FixtureRequest, Dict[str, List[SlackwarePackage]], Dict[str, List[SlackwarePackage]], PersistentList) -> str
    return _capture_stdout(
        request, list_transient_operation, local_list, remote_list, persistent_list
    )


def _capture_upgrades(request, operation, local_list, remote_list, persistent_list):
    # type: (pytest.FixtureRequest, str, Dict[str, List[SlackwarePackage]], Dict[str, List[SlackwarePackage]], PersistentList) -> str
    return _capture_stdout(
        request,
        list_upgrades_and_outdated_frozen_operation,
        operation,
        local_list,
        remote_list,
        persistent_list,
    )


# ---------------------------------------------------------------------------
# list_transient_operation tests
# ---------------------------------------------------------------------------


def test_list_transient_prints_no_transient_when_empty(request):
    # type: (pytest.FixtureRequest) -> None
    plist = tests.PersistentList({"vim": 2})  # installed - not transient
    output = _capture_list_transient(request, {}, {}, plist)
    assert "No transient packages found" in output


def test_list_transient_shows_new_pkg(request):
    # type: (pytest.FixtureRequest) -> None
    pkg = tests.build_pkg("bash", "5.2", "./slackware64/a")
    local_list = _local([])
    remote_list = _remote([pkg])
    plist = tests.PersistentList({"bash": 0})  # state_new = 0
    output = _capture_list_transient(request, local_list, remote_list, plist)
    assert "bash" in output
    assert "new" in output


def test_list_transient_shows_outdated_pkg(request):
    # type: (pytest.FixtureRequest) -> None
    local_pkg = tests.build_pkg("vim", "8.2", "./slackware64/ap")
    remote_pkg = tests.build_pkg("vim", "9.1", "./slackware64/ap")
    local_list = _local([local_pkg])
    remote_list = _remote([remote_pkg])
    plist = tests.PersistentList({"vim": 6})  # state_outdated = 6
    output = _capture_list_transient(request, local_list, remote_list, plist)
    assert "vim" in output
    assert "outdated" in output


def test_list_transient_shows_unavailable_pkg(request):
    # type: (pytest.FixtureRequest) -> None
    local_pkg = tests.build_pkg("mypkg", "1.0", "./slackware64/n")
    local_list = _local([local_pkg])
    remote_list = _remote([])  # type: Dict[str, List[SlackwarePackage]]
    plist = tests.PersistentList({"mypkg": 1})  # state_unavailable = 1
    output = _capture_list_transient(request, local_list, remote_list, plist)
    assert "mypkg" in output
    assert "unavailable" in output


def test_list_transient_non_transient_pkg_not_shown(request):
    # type: (pytest.FixtureRequest) -> None
    local_pkg = tests.build_pkg("gcc", "12.0", "./slackware64/d")
    new_pkg = tests.build_pkg("newpkg", "1.0", "./slackware64/ap")
    local_list = _local([local_pkg])
    remote_list = _remote([local_pkg, new_pkg])
    plist = tests.PersistentList({"gcc": 2, "newpkg": 0})  # gcc=installed, newpkg=new
    output = _capture_list_transient(request, local_list, remote_list, plist)
    assert "gcc" not in output
    assert "newpkg" in output


def test_list_transient_prioritized_pkg_sorts_first(request):
    # type: (pytest.FixtureRequest) -> None
    # 'aaa_glibc-solibs' is in slackroll_prioritized_pkgs, so it should appear before 'zzz-pkg'
    pkg_prio = tests.build_pkg("aaa_glibc-solibs", "2.37", "./slackware64/a")
    pkg_late = tests.build_pkg("zzz-pkg", "1.0", "./slackware64/ap")
    local_list = _local([])
    remote_list = _remote([pkg_prio, pkg_late])
    plist = tests.PersistentList({"aaa_glibc-solibs": 0, "zzz-pkg": 0})
    output = _capture_list_transient(request, local_list, remote_list, plist)
    pos_prio = output.find("aaa_glibc-solibs")
    pos_late = output.find("zzz-pkg")
    assert pos_prio != -1
    assert pos_late != -1
    assert pos_prio < pos_late


def test_list_transient_new_pkg_shows_remote_path(request):
    # type: (pytest.FixtureRequest) -> None
    pkg = tests.build_pkg("bash", "5.2", "./slackware64/a")
    local_list = _local([])
    remote_list = _remote([pkg])
    plist = tests.PersistentList({"bash": 0})
    output = _capture_list_transient(request, local_list, remote_list, plist)
    # tr_pkg_detail returns paths for new packages
    assert "./slackware64/a" in output


def test_list_transient_non_new_pkg_shows_no_path(request):
    # type: (pytest.FixtureRequest) -> None
    local_pkg = tests.build_pkg("vim", "8.2", "./slackware64/ap")
    remote_pkg = tests.build_pkg("vim", "9.1", "./slackware64/ap")
    local_list = _local([local_pkg])
    remote_list = _remote([remote_pkg])
    plist = tests.PersistentList({"vim": 6})  # outdated — tr_pkg_detail returns ''
    output = _capture_list_transient(request, local_list, remote_list, plist)
    assert "slackware64/ap" not in output


# ---------------------------------------------------------------------------
# list_upgrades_and_outdated_frozen_operation tests
# ---------------------------------------------------------------------------


def test_list_upgrades_prints_no_outdated_when_empty(request):
    # type: (pytest.FixtureRequest) -> None
    plist = tests.PersistentList({"vim": 2})  # installed
    output = _capture_upgrades(request, "list-upgrades", {}, {}, plist)
    assert "No outdated packages" in output


def test_list_outdated_frozen_prints_no_msg_when_empty(request):
    # type: (pytest.FixtureRequest) -> None
    plist = tests.PersistentList({"vim": 2})  # installed, not frozen
    output = _capture_upgrades(request, "list-outdated-frozen", {}, {}, plist)
    assert "No frozen packages would be outdated" in output


def test_list_upgrades_shows_outdated_pkg(request):
    # type: (pytest.FixtureRequest) -> None
    local_pkg = tests.build_pkg("vim", "8.2", "./slackware64/ap")
    remote_pkg = tests.build_pkg("vim", "9.1", "./slackware64/ap")
    local_list = _local([local_pkg])
    remote_list = _remote([remote_pkg])
    plist = tests.PersistentList({"vim": 6})  # state_outdated
    output = _capture_upgrades(request, "list-upgrades", local_list, remote_list, plist)
    assert "Available upgrades:" in output
    assert "vim" in output
    assert local_pkg.archivename in output
    assert remote_pkg.fullname in output


def test_list_outdated_frozen_shows_only_would_be_outdated(request):
    # type: (pytest.FixtureRequest) -> None
    # frozen_up_to_date: local version == remote version -> NOT outdated
    pkg_same = tests.build_pkg("vim", "9.1", "./slackware64/ap")
    # frozen_outdated: local version != remote version -> would be outdated
    local_old = tests.build_pkg("bash", "5.1", "./slackware64/a")
    remote_new = tests.build_pkg("bash", "5.2", "./slackware64/a")
    local_list = {
        "vim": [pkg_same],
        "bash": [local_old],
    }
    remote_list = {
        "vim": [pkg_same],
        "bash": [remote_new],
    }
    plist = tests.PersistentList({"vim": 4, "bash": 4})  # state_frozen = 4
    output = _capture_upgrades(
        request, "list-outdated-frozen", local_list, remote_list, plist
    )
    assert "Would be outdated:" in output
    assert "bash" in output
    assert "vim" not in output


def test_list_upgrades_pkg_only_in_pasture_shows_warning(request):
    # type: (pytest.FixtureRequest) -> None
    local_pkg = tests.build_pkg("oldpkg", "1.0", "./slackware64/ap")
    # Remote version is only in pasture
    remote_pkg = tests.build_pkg("oldpkg", "1.1", "./pasture/ap")
    local_list = _local([local_pkg])
    remote_list = _remote([remote_pkg])
    plist = tests.PersistentList({"oldpkg": 6})  # state_outdated
    output = _capture_upgrades(request, "list-upgrades", local_list, remote_list, plist)
    assert "only present in /pasture/" in output


def test_list_upgrades_watchout_printed_for_key_pkg(request):
    # type: (pytest.FixtureRequest) -> None
    # 'glibc-solibs' is a prioritized (key) package; upgrading it triggers watchout
    local_pkg = tests.build_pkg("glibc-solibs", "2.36", "./slackware64/a")
    remote_pkg = tests.build_pkg("glibc-solibs", "2.37", "./slackware64/a")
    local_list = _local([local_pkg])
    remote_list = _remote([remote_pkg])
    plist = tests.PersistentList({"glibc-solibs": 6})
    output = _capture_upgrades(request, "list-upgrades", local_list, remote_list, plist)
    assert "WATCH OUT" in output


def test_list_outdated_frozen_no_watchout(request):
    # type: (pytest.FixtureRequest) -> None
    # list-outdated-frozen should NOT print the key package watchout
    local_pkg = tests.build_pkg("glibc-solibs", "2.36", "./slackware64/a")
    remote_pkg = tests.build_pkg("glibc-solibs", "2.37", "./slackware64/a")
    local_list = _local([local_pkg])
    remote_list = _remote([remote_pkg])
    plist = tests.PersistentList({"glibc-solibs": 4})  # frozen
    output = _capture_upgrades(
        request, "list-outdated-frozen", local_list, remote_list, plist
    )
    assert "WATCH OUT" not in output
