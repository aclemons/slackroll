from slackroll import verify_num_args

import tests


def test_verify_num_args_zero_or_one(request):
    # type: (object) -> None

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
    # type: (object) -> None

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


def test_verify_num_args_exect(request):
    # type: (object) -> None

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
