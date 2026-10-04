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
    from typing import List


@pytest.mark.parametrize(  # type: ignore
    ("num_args", "args", "message"),
    [
        (-2, ["test", "after"], "ERROR: myop expects one argument or no arguments"),
        (-1, [], "ERROR: myop expects more arguments"),
        (0, ["arg"], "ERROR: myop expects no arguments"),
        (1, [], "ERROR: myop expects 1 argument"),
        (2, ["arg"], "ERROR: myop expects 2 arguments"),
    ],
)
def test_verify_num_args_rejects_invalid_counts(request, num_args, args, message):
    # type: (pytest.FixtureRequest, int, List[str], str) -> None
    exit_mock = tests.start_patch(request, "sys.exit")
    exit_mock.side_effect = ValueError

    pytest.raises(ValueError, verify_num_args, num_args, "myop", args)

    exit_mock.assert_called_once_with(message)


def test_verify_num_args_accepts_valid_counts():
    # type: () -> None
    verify_num_args(-2, "myop", [])
    verify_num_args(-2, "myop", ["test"])
    verify_num_args(-1, "myop", ["test"])
    verify_num_args(-1, "myop", ["test", "after"])
    verify_num_args(0, "myop", [])
    verify_num_args(1, "myop", ["after"])
    verify_num_args(2, "myop", ["after", "before"])


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
    assert (
        # spellchecker:ignore-next-line
        words_to_words_distance(["set", "miror"], ("set", "mirror")) == 1
    )
    assert words_to_words_distance(["remove"], ("remove", "repo")) == 1


def test_verify_operation_and_args_delegates_to_verify_num_args(request):
    # type: (pytest.FixtureRequest) -> None
    verify_num_args_mock = tests.start_patch(request, "slackroll.verify_num_args")

    verify_operation_and_args({"install": 1}, "install", ["vim"])

    verify_num_args_mock.assert_called_with(1, "install", ["vim"])


def test_verify_operation_and_args_suggests_closest_operation(request):
    # type: (pytest.FixtureRequest) -> None
    fake_stderr = tests.Mock()
    exit_mock = tests.start_patch(request, "sys.exit")
    tests.start_patch(request, "slackroll.sys.stderr", fake_stderr)
    exit_mock.side_effect = ValueError("boom")

    pytest.raises(
        ValueError,
        verify_operation_and_args,
        {"install": 1, "info": 1, "set-mirror": 1},
        "set-miror",  # spellchecker:disable-line
        ["vim"],
    )

    assert tests.mock_output(fake_stderr) == (
        'ERROR: no operation called "set-miror"\n'  # spellchecker:disable-line
        'Use the "help" operation to get a list.\n'
        'Did you mean "set-mirror"?\n'
    )
    exit_mock.assert_called_with(1)


def test_verify_operation_and_args_lists_sorted_tied_matches(request):
    # type: (pytest.FixtureRequest) -> None
    fake_stderr = tests.Mock()
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

    assert tests.mock_output(fake_stderr) == (
        'ERROR: no operation called "foo-bax"\n'
        'Use the "help" operation to get a list.\n'
        'Did you mean "foo-bar" or "foo-baz"?\n'
    )
    exit_mock.assert_called_with(1)
