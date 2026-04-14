import pytest
from slackroll import (
    levenshtein_distance,
    verify_num_args,
    verify_operation_and_args,
    word_to_word_list_distance,
    words_to_words_distance,
)

import tests

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False

if TYPE_CHECKING:
    pass


def test_verify_num_args_zero_or_one(request):
    # type: (pytest.FixtureRequest) -> None

    verify_num_args(-2, "myop", [])
    verify_num_args(-2, "myop", ["test"])

    exit_mock = tests.start_patch(request, "sys.exit")
    exit_mock.side_effect = ValueError

    try:
        verify_num_args(-2, "myop", ["test", "after"])
    except ValueError:
        pass
    else:
        raise ValueError("failed")

    exit_mock.assert_called_with("ERROR: myop expects one argument or no arguments")


def test_verify_num_args_any_nonzero(request):
    # type: (pytest.FixtureRequest) -> None

    verify_num_args(-1, "myop", ["test"])
    verify_num_args(-1, "myop", ["test", "after"])

    exit_mock = tests.start_patch(request, "sys.exit")
    exit_mock.side_effect = ValueError

    try:
        verify_num_args(-1, "myop", [])
    except ValueError:
        pass
    else:
        raise ValueError("failed")

    exit_mock.assert_called_with("ERROR: myop expects more arguments")


def test_verify_num_args_exact(request):
    # type: (pytest.FixtureRequest) -> None

    verify_num_args(0, "myop", [])
    verify_num_args(1, "myop", ["after"])
    verify_num_args(2, "myop", ["after", "before"])

    exit_zero_mock = tests.start_patch(request, "sys.exit")
    exit_zero_mock.side_effect = ValueError

    try:
        verify_num_args(0, "myop", ["arg"])
    except ValueError:
        pass
    else:
        raise ValueError("failed")

    exit_zero_mock.assert_called_with("ERROR: myop expects no arguments")

    exit_zero_mock.reset_mock()

    try:
        verify_num_args(1, "myop", [])
    except ValueError:
        pass
    else:
        raise ValueError("failed")

    exit_zero_mock.assert_called_with("ERROR: myop expects 1 argument")

    exit_zero_mock.reset_mock()

    try:
        verify_num_args(2, "myop", ["arg"])
    except ValueError:
        pass
    else:
        raise ValueError("failed")

    exit_zero_mock.assert_called_with("ERROR: myop expects 2 arguments")


def test_levenshtein_distance_examples():
    # type: () -> None
    assert levenshtein_distance("help", "help") == 0
    assert levenshtein_distance("help", "kelp") == 1
    assert levenshtein_distance("upgrade", "upgrades") == 1


def test_word_to_word_list_distance_picks_closest_word():
    # type: () -> None
    assert word_to_word_list_distance("upgrdae", ("install", "upgrade")) == 2
    assert word_to_word_list_distance("help", ("batch", "help", "mirror")) == 0


def test_words_to_words_distance_accounts_for_missing_words():
    # type: () -> None
    assert words_to_words_distance(["set", "miror"], ("set", "mirror")) == 1
    assert words_to_words_distance(["remove"], ("remove", "repo")) == 1


def test_verify_operation_and_args_delegates_to_verify_num_args(request):
    # type: (pytest.FixtureRequest) -> None
    verify_num_args_mock = tests.start_patch(request, "slackroll.verify_num_args")

    verify_operation_and_args({"install": 1}, "install", ["vim"])

    verify_num_args_mock.assert_called_with(1, "install", ["vim"])


def test_verify_operation_and_args_suggests_closest_operation(request):
    # type: (pytest.FixtureRequest) -> None
    fake_stderr = tests.FakeStream()
    exit_mock = tests.start_patch(request, "sys.exit")
    tests.start_patch(request, "slackroll.sys.stderr", fake_stderr)
    exit_mock.side_effect = ValueError("boom")

    pytest.raises(
        ValueError,
        verify_operation_and_args,
        {"install": 1, "info": 1, "set-mirror": 1},
        "set-miror",
        ["vim"],
    )

    assert fake_stderr.getvalue() == (
        'ERROR: no operation called "set-miror"\n'
        'Use the "help" operation to get a list.\n'
        'Did you mean "set-mirror"?\n'
    )
    exit_mock.assert_called_with(1)


def test_verify_operation_and_args_lists_sorted_tied_matches(request):
    # type: (pytest.FixtureRequest) -> None
    fake_stderr = tests.FakeStream()
    exit_mock = tests.start_patch(request, "sys.exit")
    tests.start_patch(request, "slackroll.sys.stderr", fake_stderr)
    exit_mock.side_effect = ValueError("boom")

    pytest.raises(
        ValueError,
        verify_operation_and_args,
        {"foo-bar": 0, "foo-baz": 0, "install": 1},
        "foo-bax",
        [],
    )

    assert fake_stderr.getvalue() == (
        'ERROR: no operation called "foo-bax"\n'
        'Use the "help" operation to get a list.\n'
        'Did you mean "foo-bar" or "foo-baz"?\n'
    )
    exit_mock.assert_called_with(1)
