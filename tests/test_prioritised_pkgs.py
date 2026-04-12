from slackroll import SlackwarePackage, pkg_name_cmp, sort_with_cmp, transient_cmp


def test_transient_cmp_normal_pkg_same_state():
    # type: () -> None
    left = ("python2", 6)
    right = ("python3", 6)

    assert transient_cmp(left, right) == -1
    assert transient_cmp(right, left) == 1
    assert transient_cmp(left, left) == 0


def test_transient_cmp_normal_pkg_different_state():
    # type: () -> None
    left = ("python2", 0)
    right = ("python3", 6)

    assert transient_cmp(left, right) == -1
    assert transient_cmp(right, left) == 1
    assert transient_cmp(left, left) == 0


def test_transient_cmp_prioritised_pkg_aaa_glib_solibs():
    # type: () -> None
    left = ("aaa_glibc-solibs", 0)
    right = ("python3", 6)

    assert transient_cmp(left, right) == -1
    assert transient_cmp(right, left) == 1
    assert transient_cmp(left, left) == 0


def test_transient_cmp_prioritised_pkg_glibc_solibs():
    # type: () -> None
    left = ("glibc-solibs", 0)
    right = ("python3", 6)

    assert transient_cmp(left, right) == -1
    assert transient_cmp(right, left) == 1
    assert transient_cmp(left, left) == 0


def test_transient_cmp_prioritised_pkg_sed():
    # type: () -> None
    left = ("sed", 0)
    right = ("python3", 6)

    assert transient_cmp(left, right) == -1
    assert transient_cmp(right, left) == 1
    assert transient_cmp(left, left) == 0


def test_transient_cmp_prioritised_pkg_pkgtools():
    # type: () -> None
    left = ("pkgtools", 0)
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
