"""Table tests for the pure arbitration / latch core (no rclpy)."""
import pytest

from rccar_supervisor.arbiter import Arbiter, DEFAULT_INPUTS

ADMIN = '/rccar/cmd/admin'
CAPT = '/rccar/cmd/captain'


@pytest.fixture
def arb():
    return Arbiter(dict(DEFAULT_INPUTS))


def armed(arb, now=0.0):
    ok, _ = arb.reset(arb.incident, now)
    assert ok
    return arb


def test_default_config():
    assert DEFAULT_INPUTS[ADMIN] == (100, 0.3)
    assert DEFAULT_INPUTS[CAPT] == (10, 0.5)


def test_boot_state_is_disarmed_unlatched_and_silent(arb):
    assert (arb.armed, arb.latched, arb.incident) == (False, False, 0)
    assert arb.output(0.0) is None


def test_commands_while_disarmed_never_forwarded(arb):
    arb.receive(ADMIN, 0.1, 0.5, 0.0)
    assert arb.output(0.01) is None


def test_reset_arms_and_streams_neutral_without_input(arb):
    armed(arb)
    out = arb.output(0.1)
    assert out is not None
    assert (out.heading, out.throttle, out.source) == (0.0, 0.0, '')
    assert arb.state(0.1).active_source == ''


def test_priority_selection_prefers_admin(arb):
    armed(arb)
    arb.receive(CAPT, 0.0, 0.4, 1.0)
    arb.receive(ADMIN, 0.2, 0.1, 1.0)
    out = arb.output(1.05)
    assert (out.source, out.throttle, out.heading) == ('admin', pytest.approx(0.1), 0.2)


def test_captain_used_when_admin_absent(arb):
    armed(arb)
    arb.receive(CAPT, 0.0, 0.4, 1.0)
    out = arb.output(1.1)
    assert (out.source, out.throttle) == ('captain', pytest.approx(0.4))


def test_per_input_timeout_falls_through_to_lower_priority(arb):
    armed(arb)
    arb.receive(CAPT, 0.0, 0.4, 1.0)
    arb.receive(ADMIN, 0.0, 0.1, 1.0)
    assert arb.output(1.2).source == 'admin'
    # admin timeout (0.3 s) elapsed, captain timeout (0.5 s) not yet
    assert arb.output(1.35).source == 'captain'
    # both stale -> neutral, still streaming
    out = arb.output(1.6)
    assert (out.source, out.throttle) == ('', 0.0)


def test_unknown_input_is_ignored(arb):
    armed(arb)
    arb.receive('/rccar/cmd/rogue', 0.0, 1.0, 1.0)
    assert arb.output(1.0).throttle == 0.0


def test_throttle_and_heading_sanitised(arb):
    armed(arb)
    arb.receive(ADMIN, float('nan'), 5.0, 1.0)
    out = arb.output(1.0)
    assert out.throttle == 1.0 and out.heading == 0.0


@pytest.mark.parametrize('how', ['brake', 'disarm', 'failsafe'])
def test_latch_on_brake_disarm_failsafe(arb, how):
    armed(arb)
    arb.receive(ADMIN, 0.0, 0.2, 1.0)
    inc = arb.incident
    assert getattr(arb, how)('why') is True
    assert arb.incident == inc + 1
    assert arb.latched and not arb.armed
    assert arb.output(1.01) is None
    st = arb.state(1.01)
    assert st.estop_latched and not st.armed and st.reason == 'why'


def test_latch_is_idempotent_while_latched(arb):
    armed(arb)
    arb.brake('first')
    inc = arb.incident
    assert arb.failsafe('late mcu event') is False
    assert arb.incident == inc
    assert arb.state(0).reason == 'first'


def test_disarm_from_boot_latches_incident(arb):
    assert arb.disarm('operator') is True
    assert arb.incident == 1 and arb.latched


def test_reset_refused_for_stale_incident(arb):
    armed(arb)
    arb.brake('x')
    ok, msg = arb.reset(arb.incident - 1, 2.0)
    assert not ok and 'stale' in msg
    assert not arb.armed and arb.latched


def test_reset_refused_when_admin_throttle_nonneutral(arb):
    armed(arb)
    arb.brake('x')
    arb.receive(ADMIN, 0.0, 0.2, 2.0)
    ok, msg = arb.reset(arb.incident, 2.05)
    assert not ok and 'neutral' in msg
    assert not arb.armed


def test_reset_allowed_when_nonneutral_admin_is_stale(arb):
    armed(arb)
    arb.brake('x')
    arb.receive(ADMIN, 0.0, 0.2, 2.0)
    ok, _ = arb.reset(arb.incident, 3.0)
    assert ok


def test_reset_allowed_when_admin_neutral(arb):
    armed(arb)
    arb.brake('x')
    arb.receive(ADMIN, 0.0, 0.04, 2.0)
    ok, _ = arb.reset(arb.incident, 2.05)
    assert ok and arb.armed and not arb.latched


def test_fence_ignores_pre_reset_commands(arb):
    armed(arb)
    arb.brake('x')
    arb.receive(CAPT, 0.0, 0.4, 2.0)          # old goal, still fresh at reset
    ok, _ = arb.reset(arb.incident, 2.1)
    assert ok
    out = arb.output(2.11)
    assert (out.source, out.throttle) == ('', 0.0)
    arb.receive(CAPT, 0.0, 0.4, 2.2)          # new command after reset is accepted
    assert arb.output(2.21).throttle == pytest.approx(0.4)


def test_latch_during_armed_clears_forwarding_and_reset_clears_latch_state(arb):
    armed(arb)
    arb.receive(ADMIN, 0.0, 0.3, 1.0)
    arb.disarm('d')
    assert arb.state(1.0).active_source == ''
    ok, _ = arb.reset(arb.incident, 5.0)
    assert ok
    assert arb.state(5.0).reason == ''


def test_reset_when_already_armed_is_idempotent(arb):
    armed(arb)
    ok, _ = arb.reset(arb.incident, 1.0)
    assert ok and arb.armed


def test_state_reason_truncated(arb):
    arb.disarm('x' * 200)
    assert len(arb.state(0).reason) <= 64
