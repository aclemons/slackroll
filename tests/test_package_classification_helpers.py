from slackroll import (
    any_in_extra_tree,
    any_in_main_tree,
    key_pkg_activity_pending,
    key_pkg_in,
    key_transient_pkgs,
    maybe_print_key_pkg_warning,
    maybe_print_key_pkg_watchout,
    maybe_print_new_warning,
    maybe_print_outdated_warning,
    not_main,
    not_main_or_extra,
    not_pasture,
    pkgs_in_state,
    slackroll_state_foreign,
    slackroll_state_new,
    slackroll_state_notinstalled,
    slackroll_state_outdated,
    tr_pkg_detail,
)

import tests


def test_tree_presence_helpers_detect_main_and_extra_packages():
    # type: () -> None
    main_pkg = tests.build_pkg("vim", "1.0", "./slackware64/ap")
    extra_pkg = tests.build_pkg("flash-player-plugin", "1.0", "./extra/packages")
    repo_pkg = tests.build_pkg("thirdparty", "1.0", "./testing/packages")

    assert any_in_main_tree([main_pkg, repo_pkg]) is True
    assert any_in_main_tree([repo_pkg]) is False
    assert any_in_extra_tree([extra_pkg, repo_pkg]) is True
    assert any_in_extra_tree([main_pkg, repo_pkg]) is False


def test_tree_filter_helpers_remove_expected_packages():
    # type: () -> None
    main_pkg = tests.build_pkg("vim", "1.0", "./slackware64/ap")
    extra_pkg = tests.build_pkg("flash-player-plugin", "1.0", "./extra/packages")
    pasture_pkg = tests.build_pkg("oldpkg", "1.0", "./pasture/ap")
    repo_pkg = tests.build_pkg("thirdparty", "1.0", "./testing/packages")

    assert not_pasture([main_pkg, pasture_pkg, repo_pkg]) == [main_pkg, repo_pkg]
    assert not_main([main_pkg, extra_pkg, repo_pkg]) == [extra_pkg, repo_pkg]
    assert not_main_or_extra([main_pkg, extra_pkg, repo_pkg]) == [repo_pkg]


def test_state_and_key_package_helpers_identify_matching_names():
    # type: () -> None
    persistent_list = {
        "aaa_glibc-solibs": slackroll_state_new,
        "pkgtools": slackroll_state_outdated,
        "vim": slackroll_state_notinstalled,
        "thirdparty": slackroll_state_foreign,
    }

    assert pkgs_in_state(
        persistent_list, [slackroll_state_new, slackroll_state_outdated]
    ) == [
        "aaa_glibc-solibs",
        "pkgtools",
    ]
    assert key_pkg_in(["vim", "pkgtools"]) is True
    assert key_pkg_in(["vim", "thirdparty"]) is False
    assert key_transient_pkgs(persistent_list) == ["aaa_glibc-solibs", "pkgtools"]
    assert key_pkg_activity_pending(persistent_list) is True


def test_maybe_print_key_package_messages_when_activity_pending(request):
    # type: (object) -> None
    fake_stdout = tests.FakeStream()
    tests.start_patch(request, "slackroll.sys.stdout", fake_stdout)
    persistent_list = {
        "aaa_glibc-solibs": slackroll_state_new,
    }

    assert maybe_print_key_pkg_watchout(persistent_list) is True
    assert maybe_print_key_pkg_warning(persistent_list) is True
    assert fake_stdout.getvalue() == (
        "\nWATCH OUT: ACTIVITY IN KEY SYSTEM PACKAGES\n"
        'You can upgrade them using "upgrade-key-packages"\n\n'
        "WARNING: It seems there is activity in key system packages\n"
        'WARNING: You should probably use "upgrade-key-packages" first\n'
    )


def test_maybe_print_new_and_outdated_warnings(request):
    # type: (object) -> None
    fake_stdout = tests.FakeStream()
    tests.start_patch(request, "slackroll.sys.stdout", fake_stdout)
    persistent_list = {
        "newpkg": slackroll_state_new,
        "oldpkg": slackroll_state_outdated,
    }

    assert maybe_print_new_warning(persistent_list) is True
    assert maybe_print_outdated_warning(persistent_list) is True
    assert fake_stdout.getvalue() == (
        "WARNING: There are new packages\nWARNING: There are outdated packages\n"
    )


def test_warning_helpers_return_false_without_matching_packages(request):
    # type: (object) -> None
    fake_stdout = tests.FakeStream()
    tests.start_patch(request, "slackroll.sys.stdout", fake_stdout)
    persistent_list = {
        "vim": slackroll_state_notinstalled,
    }

    assert maybe_print_key_pkg_watchout(persistent_list) is False
    assert maybe_print_key_pkg_warning(persistent_list) is False
    assert maybe_print_new_warning(persistent_list) is False
    assert maybe_print_outdated_warning(persistent_list) is False
    assert fake_stdout.getvalue() == ""


def test_tr_pkg_detail_returns_remote_paths_for_new_packages_only():
    # type: () -> None
    remote_list = {
        "vim": [
            tests.build_pkg("vim", "1.0", "./slackware64/ap"),
            tests.build_pkg("vim", "2.0", "./patches/packages"),
        ]
    }

    assert tr_pkg_detail({}, remote_list, {"vim": slackroll_state_new}, "vim") == (
        "./slackware64/ap ./patches/packages"
    )
    assert (
        tr_pkg_detail({}, remote_list, {"vim": slackroll_state_notinstalled}, "vim")
        == ""
    )
