import pytest
from slackroll import SlackwarePackage, pkg_name_cmp, sort_with_cmp, transient_cmp

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Tuple


@pytest.mark.parametrize(  # type: ignore
    "left",
    [
        ("python2", 6),
        ("python2", 0),
        ("aaa_glibc-solibs", 0),
        ("glibc-solibs", 0),
        ("sed", 0),
        ("pkgtools", 0),
    ],
    ids=[
        "normal-same-state",
        "normal-different-state",
        "aaa_glibc-solibs-priority",
        "glibc-solibs-priority",
        "sed-priority",
        "pkgtools-priority",
    ],
)
def test_transient_cmp_orders_package_before_python3(left):
    # type: (Tuple[str, int]) -> None
    right = ("python3", 6)

    assert transient_cmp(left, right) == -1
    assert transient_cmp(right, left) == 1
    assert transient_cmp(left, left) == 0


def test_sort_with_cmp_orders_prioritised_packages_first():
    # type: () -> None
    names = ["python3", "glibc-solibs", "sed", "aaa_glibc-solibs"]

    sort_with_cmp(names, pkg_name_cmp)

    assert names == ["aaa_glibc-solibs", "glibc-solibs", "sed", "python3"]


def test_slackware_package_sort_uses_prioritised_name_order():
    # type: () -> None
    packages = [
        SlackwarePackage("python3", "1.0", "x86_64", "1", "./a", ".txz", None, None),
        SlackwarePackage(
            "glibc-solibs", "1.0", "x86_64", "1", "./a", ".txz", None, None
        ),
        SlackwarePackage(
            "aaa_glibc-solibs", "1.0", "x86_64", "1", "./a", ".txz", None, None
        ),
    ]

    packages.sort()

    assert [pkg.name for pkg in packages] == [
        "aaa_glibc-solibs",
        "glibc-solibs",
        "python3",
    ]
