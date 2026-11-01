"""link_level decision table."""
from rccar_drivers.slamtec.diagnostics import ERROR, link_level, OK, WARN
from rccar_drivers.slamtec.protocol import Health


def test_link_down_is_error():
    assert link_level(False, Health()) == (ERROR, 'disconnected, retrying')


def test_no_health_yet_is_ok():
    assert link_level(True, None)[0] == OK


def test_ok():
    assert link_level(True, Health()) == (OK, 'ok')


def test_error_flags():
    assert link_level(True, Health(has_fatal=True))[0] == ERROR
    assert link_level(True, Health(has_error=True))[0] == ERROR
    assert link_level(True, Health(has_error=True, has_warning=True))[0] == ERROR


def test_warn_flags():
    assert link_level(True, Health(has_warning=True))[0] == WARN
    assert link_level(True, Health(has_lidar_disconnected=True))[0] == WARN
