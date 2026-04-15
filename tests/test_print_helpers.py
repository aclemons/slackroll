import pytest
from slackroll import (
    print_in_states,
    print_in_states_or,
    print_list,
    print_list_or,
    print_seq,
    print_seq_or,
    slackroll_state_installed,
    slackroll_state_new,
    slackroll_state_outdated,
)

import tests


def test_print_in_states_prints_sorted_names_without_states(request):
    # type: (pytest.FixtureRequest) -> None
    fake_stdout = tests.FakeStream()
    tests.start_patch(request, "slackroll.sys.stdout", fake_stdout)
    persistent_list = {
        "python3": slackroll_state_new,
        "aaa_glibc-solibs": slackroll_state_new,
        "vim": slackroll_state_installed,
    }

    print_in_states([slackroll_state_new], persistent_list, "New packages:", False)

    assert fake_stdout.getvalue() == (
        "New packages:\n    aaa_glibc-solibs\n    python3\nEnd of list\n"
    )


def test_print_in_states_prints_state_labels(request):
    # type: (pytest.FixtureRequest) -> None
    fake_stdout = tests.FakeStream()
    tests.start_patch(request, "slackroll.sys.stdout", fake_stdout)
    persistent_list = {
        "python3": slackroll_state_outdated,
        "aaa_glibc-solibs": slackroll_state_new,
    }

    print_in_states(
        [slackroll_state_new, slackroll_state_outdated],
        persistent_list,
        "Transient packages:",
        True,
    )

    assert fake_stdout.getvalue() == (
        "Transient packages:\n"
        "    new            aaa_glibc-solibs\n"
        "    outdated       python3\n"
        "End of list\n"
    )


def test_print_in_states_or_prints_empty_message_without_interceptor(request):
    # type: (pytest.FixtureRequest) -> None
    fake_stdout = tests.FakeStream()
    interceptor_mock = tests.start_patch(
        request, "slackroll.SlackrollOutputInterceptor"
    )
    tests.start_patch(request, "slackroll.sys.stdout", fake_stdout)

    print_in_states_or([slackroll_state_new], {}, "Header", "No matches", False)

    assert fake_stdout.getvalue() == "No matches\n"
    assert interceptor_mock.called is False


def test_print_in_states_or_uses_interceptor_for_nonempty_output(request):
    # type: (pytest.FixtureRequest) -> None
    interceptor = tests.start_patch(request, "slackroll.SlackrollOutputInterceptor")
    print_in_states_mock = tests.start_patch(request, "slackroll.print_in_states")
    persistent_list = {"vim": slackroll_state_new}

    print_in_states_or([slackroll_state_new], persistent_list, "Header", "Empty", False)

    assert interceptor.called is True
    print_in_states_mock.assert_called_with(
        [slackroll_state_new], persistent_list, "Header", False
    )
    interceptor.return_value.stop.assert_called_with()


def test_print_seq_sorts_prioritized_names(request):
    # type: (pytest.FixtureRequest) -> None
    fake_stdout = tests.FakeStream()
    tests.start_patch(request, "slackroll.sys.stdout", fake_stdout)

    print_seq(set(["python3", "sed", "aaa_glibc-solibs"]), "Sequence:")

    assert fake_stdout.getvalue() == (
        "Sequence:\n    aaa_glibc-solibs\n    sed\n    python3\nEnd of list\n"
    )


def test_print_seq_or_prints_empty_message_or_uses_interceptor(request):
    # type: (pytest.FixtureRequest) -> None
    fake_stdout = tests.FakeStream()
    interceptor_mock = tests.start_patch(
        request, "slackroll.SlackrollOutputInterceptor"
    )
    print_seq_mock = tests.start_patch(request, "slackroll.print_seq")
    tests.start_patch(request, "slackroll.sys.stdout", fake_stdout)

    print_seq_or([], "Header", "Nothing here")
    assert fake_stdout.getvalue() == "Nothing here\n"
    assert interceptor_mock.called is False

    fake_stdout.messages = []
    print_seq_or(["vim"], "Header", "Nothing here")
    assert fake_stdout.getvalue() == ""
    assert interceptor_mock.called is True
    print_seq_mock.assert_called_with(["vim"], "Header")
    interceptor_mock.return_value.stop.assert_called_with()


def test_print_list_and_print_list_or_sort_entries(request):
    # type: (pytest.FixtureRequest) -> None
    fake_stdout = tests.FakeStream()
    interceptor_mock = tests.start_patch(
        request, "slackroll.SlackrollOutputInterceptor"
    )
    tests.start_patch(request, "slackroll.sys.stdout", fake_stdout)

    entries = ["zeta", "alpha", "beta"]
    print_list(entries, "Entries:")

    assert fake_stdout.getvalue() == (
        "Entries:\n    alpha\n    beta\n    zeta\nEnd of list\n"
    )
    assert entries == ["alpha", "beta", "zeta"]

    fake_stdout.messages = []
    print_list_or([], "Entries:", "No entries")
    assert fake_stdout.getvalue() == "No entries\n"

    fake_stdout.messages = []
    print_list_or(["beta", "alpha"], "Entries:", "No entries")
    assert interceptor_mock.called is True
    interceptor_mock.return_value.stop.assert_called_with()
