import pytest
from slackroll import post_kernel_operation

import tests

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Dict, List, Optional, Sequence, Tuple


class FakePwdEntry(object):
    def __init__(self, shell):
        # type: (str) -> None
        self.pw_shell = shell


def test_post_kernel_operation_batch_mode_warns_and_returns(request):
    # type: (pytest.FixtureRequest) -> None
    fake_stdout = tests.FakeStream()

    tests.start_patch(request, "slackroll.sys.stdout", fake_stdout)
    tests.start_patch(request, "slackroll.slackroll_batch_mode", True)

    post_kernel_operation()

    assert fake_stdout.getvalue() == (
        "WARNING: you may need to modify your bootloader configuration and reboot\n"
    )


def test_post_kernel_operation_runs_visual_lilo_and_shell_actions(request):
    # type: (pytest.FixtureRequest) -> None
    fake_stdout = tests.FakeStream()
    option_calls = []  # type: List[List[Tuple[str, str]]]
    visual_calls = []  # type: List[str]
    program_calls = []  # type: List[Tuple[List[str], Optional[Dict[str, str]]]]
    choices = [0, 1, 2, 3]

    def fake_exists(path):
        # type: (str) -> bool
        return path in ["/etc/lilo.conf", "/sbin/lilo"]

    def fake_choose_option(options):
        # type: (List[Tuple[str, str]]) -> int
        option_calls.append(list(options))
        return choices.pop(0)

    def fake_run_visual_on(path):
        # type: (str) -> None
        visual_calls.append(path)

    def fake_run_program(args, env=None):
        # type: (List[str], Optional[Dict[str, str]]) -> None
        program_calls.append((args, env))

    tests.start_patch(request, "slackroll.sys.stdout", fake_stdout)
    tests.start_patch(request, "slackroll.slackroll_batch_mode", False)
    tests.start_patch(
        request, "slackroll.slackroll_bootloader_config_files", ["/etc/lilo.conf"]
    )
    tests.start_patch(request, "slackroll.slackroll_lilo_path", "/sbin/lilo")
    tests.start_patch(request, "slackroll.os.path.exists", fake_exists)
    tests.start_patch(request, "slackroll.get_visual", lambda: "vim")
    tests.start_patch(request, "slackroll.choose_option", fake_choose_option)
    tests.start_patch(request, "slackroll.run_visual_on", fake_run_visual_on)
    tests.start_patch(request, "slackroll.run_program", fake_run_program)
    tests.start_patch(request, "slackroll.os.geteuid", lambda: 0)
    tests.start_patch(
        request, "slackroll.pwd.getpwuid", lambda _uid: FakePwdEntry("/bin/sh")
    )
    tests.start_patch(request, "slackroll.os.environ", {"TERM": "xterm"})

    post_kernel_operation()

    assert visual_calls == ["/etc/lilo.conf"]
    assert program_calls[0] == (["/sbin/lilo"], None)
    assert program_calls[1][0] == ["/bin/sh"]
    assert program_calls[1][1] is not None
    assert program_calls[1][1]["TERM"] == "xterm"
    assert program_calls[1][1]["PS1"] == "(slackroll) sh% "
    assert option_calls[0] == [
        ("1", "vim /etc/lilo.conf"),
        ("L", "/sbin/lilo"),
        ("S", "Shell"),
        ("X", "Done"),
    ]
    assert fake_stdout.getvalue() == "\n\n\n"
