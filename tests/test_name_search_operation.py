# -*- coding: utf-8 -*-

from slackroll import name_search_operation, slackroll_state_installed

import tests

# This fixture uses escaped UTF-8 bytes to model slackroll's internal
# lossless text representation; the search argument below stays readable
# because it represents what the user types at the CLI.
if tests.PY2:
    multibyte_package_name = tests.bytes_literal(
        "ca-certificates-F\xc5\x91tan\xc3\xbas\xc3\xadtv\xc3\xa1ny"
    )
else:
    multibyte_package_name = tests.decode_bytes_literal(
        "ca-certificates-F\xc5\x91tan\xc3\xbas\xc3\xadtv\xc3\xa1ny",
        "latin-1",
    )


class FakeStdout(tests.FakeStream):
    def isatty(self):
        # type: () -> bool
        return False


def test_name_search_operation_matches_multibyte_package_names(request):
    # type: (object) -> None
    fake_stdout = FakeStdout()
    persistent_list = {
        multibyte_package_name: slackroll_state_installed,
        "bash": slackroll_state_installed,
    }

    tests.start_patch(request, "slackroll.sys.stdout", fake_stdout)

    name_search_operation(["Főtanúsítvány"], persistent_list)

    output = fake_stdout.getvalue()
    assert "Matching packages:\n" in output
    assert multibyte_package_name in output
    assert "bash" not in output
