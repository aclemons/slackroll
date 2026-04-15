import pytest
from slackroll import (
    from_states_to_state,
    slackroll_exit_failure,
    slackroll_state_frozen,
    slackroll_state_installed,
    slackroll_state_new,
    slackroll_state_notinstalled,
)

import tests

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False

if TYPE_CHECKING:
    pass


def test_from_states_to_state_updates_allowed_packages(request):
    # type: (pytest.FixtureRequest) -> None
    fake_stdout = tests.FakeStream()
    tests.start_patch(request, "slackroll.sys.stdout", fake_stdout)
    persistent_list = tests.PersistentList({"vim": slackroll_state_new})

    from_states_to_state(
        [slackroll_state_new],
        slackroll_state_notinstalled,
        tests.persistent_dict(persistent_list),
        ["vim"],
    )

    assert persistent_list == {"vim": slackroll_state_notinstalled}
    assert persistent_list.sync_calls == 1
    assert fake_stdout.getvalue() == "Marking packages as not-installed...\n"


def test_from_states_to_state_keeps_disallowed_states_and_warns(request):
    # type: (pytest.FixtureRequest) -> None
    fake_stdout = tests.FakeStream()
    tests.start_patch(request, "slackroll.sys.stdout", fake_stdout)
    persistent_list = tests.PersistentList({"vim": slackroll_state_installed})

    from_states_to_state(
        [slackroll_state_frozen],
        slackroll_state_notinstalled,
        tests.persistent_dict(persistent_list),
        ["vim"],
    )

    assert persistent_list == {"vim": slackroll_state_installed}
    assert persistent_list.sync_calls == 1
    assert fake_stdout.getvalue() == (
        "Marking packages as not-installed...\n"
        "vim: cannot change state from installed to not-installed\n"
    )


def test_from_states_to_state_errors_for_unknown_packages(request):
    # type: (pytest.FixtureRequest) -> None
    fake_stderr = tests.FakeStream()
    exit_mock = tests.start_patch(request, "sys.exit")
    tests.start_patch(request, "slackroll.sys.stderr", fake_stderr)
    exit_mock.side_effect = ValueError("boom")
    persistent_list = tests.PersistentList({"vim": slackroll_state_installed})

    pytest.raises(
        ValueError,
        from_states_to_state,
        [slackroll_state_installed],
        slackroll_state_notinstalled,
        tests.persistent_dict(persistent_list),
        ["ghost-1.0-x86_64-1.txz"],
    )

    assert persistent_list == {"vim": slackroll_state_installed}
    assert persistent_list.sync_calls == 0
    assert fake_stderr.getvalue() == (
        "WARNING: ghost-1.0-x86_64-1.txz looks like an unexpected full version\n"
        "ERROR: The following packages are unknown:\n"
        "ERROR:    ghost-1.0-x86_64-1.txz\n"
    )
    exit_mock.assert_called_with(slackroll_exit_failure)
