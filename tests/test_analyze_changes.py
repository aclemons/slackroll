from slackroll import (
    analyze_changes,
    slackroll_state_foreign,
    slackroll_state_installed,
    slackroll_state_new,
    slackroll_state_notinstalled,
    slackroll_state_outdated,
    slackroll_state_unavailable,
)

import tests

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Dict, List

    from slackroll import SlackwarePackage


def test_analyze_changes_marks_matching_local_and_remote_package_installed():
    # type: () -> None
    local_list = {
        "vim": [tests.build_pkg("vim", "1.0", "./slackware64/ap")],
    }  # type: Dict[str, List[SlackwarePackage]]
    remote_list = {
        "vim": [tests.build_pkg("vim", "1.0", "./slackware64/ap")],
    }  # type: Dict[str, List[SlackwarePackage]]
    persistent_list = tests.PersistentList({"vim": slackroll_state_new})

    analyze_changes(local_list, remote_list, tests.persistent_dict(persistent_list))

    assert persistent_list == {"vim": slackroll_state_installed}
    assert persistent_list.sync_calls == 1


def test_analyze_changes_marks_existing_local_package_outdated_when_remote_differs():
    # type: () -> None
    local_list = {
        "vim": [tests.build_pkg("vim", "1.0", "./slackware64/ap")],
    }  # type: Dict[str, List[SlackwarePackage]]
    remote_list = {
        "vim": [tests.build_pkg("vim", "2.0", "./slackware64/ap")],
    }  # type: Dict[str, List[SlackwarePackage]]
    persistent_list = tests.PersistentList({"vim": slackroll_state_foreign})

    analyze_changes(local_list, remote_list, tests.persistent_dict(persistent_list))

    assert persistent_list == {"vim": slackroll_state_outdated}
    assert persistent_list.sync_calls == 1


def test_analyze_changes_classifies_remote_only_packages_by_visibility():
    # type: () -> None
    local_list = {}  # type: Dict[str, List[SlackwarePackage]]
    remote_list = {
        "available": [tests.build_pkg("available", "1.0", "./slackware64/ap")],
        "pasture-only": [tests.build_pkg("pasture-only", "1.0", "./pasture/ap")],
        "restored": [tests.build_pkg("restored", "1.0", "./slackware64/ap")],
        "removed-local": [tests.build_pkg("removed-local", "1.0", "./slackware64/ap")],
    }  # type: Dict[str, List[SlackwarePackage]]
    persistent_list = tests.PersistentList(
        {
            "restored": slackroll_state_unavailable,
            "removed-local": slackroll_state_installed,
        }
    )

    analyze_changes(local_list, remote_list, tests.persistent_dict(persistent_list))

    assert persistent_list == {
        "available": slackroll_state_new,
        "pasture-only": slackroll_state_notinstalled,
        "restored": slackroll_state_new,
        "removed-local": slackroll_state_notinstalled,
    }
    assert persistent_list.sync_calls == 1


def test_analyze_changes_marks_missing_local_packages_unavailable_and_deletes_orphans():
    # type: () -> None
    local_list = {
        "vim": [tests.build_pkg("vim", "1.0", "./slackware64/ap")],
    }  # type: Dict[str, List[SlackwarePackage]]
    remote_list = {}  # type: Dict[str, List[SlackwarePackage]]
    persistent_list = tests.PersistentList(
        {
            "vim": slackroll_state_installed,
            "gone": slackroll_state_new,
        }
    )

    analyze_changes(local_list, remote_list, tests.persistent_dict(persistent_list))

    assert persistent_list == {"vim": slackroll_state_unavailable}
    assert persistent_list.sync_calls == 1
