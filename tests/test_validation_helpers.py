import pytest
from slackroll import verify_local_names

import tests

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Dict, List

    from slackroll import SlackwarePackage


def test_verify_local_names_accepts_known_names():
    # type: () -> None
    local_list = {"vim": [tests.build_pkg("vim", "9.1", "/var/log/packages")]}  # type: Dict[str, List[SlackwarePackage]]

    verify_local_names(["vim"], local_list)


def test_verify_local_names_warns_for_unexpected_full_version(request):
    # type: (pytest.FixtureRequest) -> None
    fake_stdout = tests.FakeStream()
    exit_mock = tests.start_patch(request, "sys.exit")
    tests.start_patch(request, "slackroll.sys.stdout", fake_stdout)
    exit_mock.side_effect = ValueError("boom")

    pytest.raises(
        ValueError,
        verify_local_names,
        ["ghost-1.0-x86_64-1.txz"],
        {},
    )

    assert fake_stdout.getvalue() == (
        "WARNING: ghost-1.0-x86_64-1.txz looks like an unexpected full version\n"
    )
    exit_mock.assert_called_with(
        "ERROR: ghost-1.0-x86_64-1.txz is not a local package name"
    )


def test_verify_local_names_errors_for_plain_unknown_name(request):
    # type: (pytest.FixtureRequest) -> None
    fake_stdout = tests.FakeStream()
    exit_mock = tests.start_patch(request, "sys.exit")
    tests.start_patch(request, "slackroll.sys.stdout", fake_stdout)
    exit_mock.side_effect = ValueError("boom")

    pytest.raises(ValueError, verify_local_names, ["ghost"], {})

    assert fake_stdout.getvalue() == ""
    exit_mock.assert_called_with("ERROR: ghost is not a local package name")
