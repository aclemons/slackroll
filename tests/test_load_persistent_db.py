import os
import shutil
from tempfile import mkdtemp

import pytest
from slackroll import load_persistent_db, slackroll_state_installed

import tests


@pytest.fixture  # type: ignore
def temp_dir(request):
    # type: (pytest.FixtureRequest) -> str
    dir = mkdtemp()

    def teardown():
        # type: () -> None
        shutil.rmtree(dir)

    request.addfinalizer(teardown)
    return dir


if tests.PY2:

    def test_switch_format(temp_dir, request):
        # type: (str, pytest.FixtureRequest) -> None
        """Checks if we can open a known good file."""

        tests.start_patch(request, "slackroll.get_temp_dir", lambda: temp_dir)
        data_file = os.path.join(temp_dir, "test.db")

        shutil.copy2(
            os.path.join(os.path.dirname(__file__), "..", "data", "py2_persistent.db"),
            data_file,
        )

        data = load_persistent_db(data_file)

        assert dict(data) == {
            "python2": slackroll_state_installed,
            "python3": slackroll_state_installed,
        }

        data.close()


def test_round_trip_serialisation(temp_dir, request):
    # type: (str, pytest.FixtureRequest) -> None
    """Checks if we can round trip serialise then deserialise a value."""

    tests.start_patch(request, "slackroll.get_temp_dir", lambda: temp_dir)
    data_file = os.path.join(temp_dir, "test.db")

    data = load_persistent_db(data_file)

    data["package1"] = slackroll_state_installed
    data["package2"] = slackroll_state_installed

    data.close()

    data = load_persistent_db(data_file)

    assert dict(data) == {
        "package1": slackroll_state_installed,
        "package2": slackroll_state_installed,
    }

    if tests.PY2:
        assert "package1".decode("latin-1") in data
        assert data["package1".decode("latin-1")] == slackroll_state_installed

    data.close()
