from slackroll import get_self_file_version, write_self_file_version

import tests


def test_round_trip_serialisation(request):
    # type: (object) -> None
    """Checks if we can round trip write the self file version and then read it again."""

    version = 42

    f = tests.named_temporary_file(delete=True)

    tests.start_patch(request, "slackroll.slackroll_version", version)
    tests.start_patch(request, "slackroll.slackroll_self_filename", f.name)
    write_self_file_version()

    assert version == get_self_file_version()

    f.close()
