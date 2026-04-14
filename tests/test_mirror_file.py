import pytest
from slackroll import (
    get_default_primary_mirror,
    get_mirror_from_file,
    get_mirror_version_components,
    get_primary_mirror,
)

import tests

if tests.PY2:
    non_utf8_latin1 = "\xb3\xb7\xd8\xd9"
else:
    non_utf8_latin1 = tests.decode_bytes_literal("\xb3\xb7\xd8\xd9", "latin-1")


def test_get_mirror_from_file_adds_trailing_slash():
    # type: () -> None
    f = tests.named_temporary_file(delete=True)
    try:
        f.write(tests.bytes_literal("https://example.invalid\n"))
        f.flush()

        assert get_mirror_from_file(f.name) == "https://example.invalid/"
    finally:
        f.close()


def test_get_mirror_from_file_preserves_non_utf8_bytes():
    # type: () -> None
    f = tests.named_temporary_file(delete=True)
    try:
        f.write(tests.bytes_literal("https://example.\xb3\xb7\xd8\xd9\n"))
        f.flush()

        mirror = get_mirror_from_file(f.name)

        assert mirror == "https://example.%s/" % non_utf8_latin1
        if not tests.PY2:
            assert tests.bytes_literal("\xb3\xb7\xd8\xd9") in mirror.encode("latin-1")
    finally:
        f.close()


def test_get_mirror_from_file_rejects_multiple_lines():
    # type: () -> None
    f = tests.named_temporary_file(delete=True)
    try:
        f.write(
            tests.bytes_literal("https://example.invalid\nhttps://example2.invalid\n")
        )
        f.flush()

        pytest.raises(SystemExit, get_mirror_from_file, f.name)
    finally:
        f.close()


def test_get_primary_mirror_prefers_primary_mirror_file(request):
    # type: (pytest.FixtureRequest) -> None
    tests.start_patch(request, "slackroll.is_readable_file", lambda _path: True)
    get_mirror_from_file_mock = tests.start_patch(
        request, "slackroll.get_mirror_from_file"
    )
    get_mirror_from_file_mock.return_value = "https://primary.example.invalid/"

    assert get_primary_mirror() == "https://primary.example.invalid/"
    assert get_mirror_from_file_mock.call_count == 1


def test_get_primary_mirror_falls_back_to_default_for_x86_64(request):
    # type: (pytest.FixtureRequest) -> None
    tests.start_patch(request, "slackroll.is_readable_file", lambda _path: False)
    tests.start_patch(
        request,
        "slackroll.get_mirror",
        lambda: "https://slackware.osuosl.org/slackware64-15.0/",
    )

    assert (
        get_primary_mirror()
        == "http://ftp.slackware.com/pub/slackware/slackware64-15.0/"
    )


def test_get_default_primary_mirror_uses_arm_site_for_aarch64():
    # type: () -> None
    assert (
        get_default_primary_mirror("aarch64", "15.0")
        == "http://ftp.arm.slackware.com/slackwarearm/slackwareaarch64-15.0/"
    )


def test_get_default_primary_mirror_uses_arm_site():
    # type: () -> None
    assert (
        get_default_primary_mirror("arm", "15.0")
        == "http://ftp.arm.slackware.com/slackwarearm/slackwarearm-15.0/"
    )


def test_get_mirror_version_components_extracts_arch_and_version():
    # type: () -> None
    assert get_mirror_version_components(
        "https://slackware.osuosl.org/slackware64-15.0/"
    ) == (
        "64",
        "15.0",
    )
    assert get_mirror_version_components(
        "https://arm.example.invalid/slackwareaarch64-current/"
    ) == (
        "aarch64",
        "current",
    )


def test_get_mirror_version_components_rejects_invalid_mirror(request):
    # type: (pytest.FixtureRequest) -> None
    exit_mock = tests.start_patch(request, "sys.exit")
    exit_mock.side_effect = ValueError("boom")

    pytest.raises(
        ValueError,
        get_mirror_version_components,
        "https://example.invalid/not-slackware/",
    )

    exit_mock.assert_called_with(
        "ERROR: unable to extract Slackware version from mirror name"
    )
