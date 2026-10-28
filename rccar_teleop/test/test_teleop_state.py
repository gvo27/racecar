"""Key decoding and teleop state logic (pure)."""
import pytest

from rccar_teleop.teleop_state import KeyDecoder, TeleopState


def test_decoder_plain_and_arrows():
    d = KeyDecoder()
    assert d.feed('a ') == ['a', ' ']
    assert d.feed('\x1b[A\x1b[B\x1b[C\x1b[D') == ['up', 'down', 'right', 'left']


def test_decoder_split_escape_sequence():
    d = KeyDecoder()
    assert d.feed('\x1b') == []
    assert d.feed('[A') == ['up']


def test_decoder_ss3_arrows_and_unknown_sequence_dropped():
    d = KeyDecoder()
    assert d.feed('\x1bOA') == ['up']
    assert d.feed('\x1b[3~z') == ['z']


def test_decoder_lone_escape_flush():
    d = KeyDecoder()
    d.feed('\x1b')
    assert d.flush() == ['esc']


def make():
    return TeleopState(max_throttle=0.3, throttle_step=0.05, heading_step=0.1,
                       max_heading=0.5)


def test_throttle_steps_and_clamp():
    s = make()
    for _ in range(10):
        s.handle('up')
    assert s.throttle == pytest.approx(0.3)
    for _ in range(20):
        s.handle('down')
    assert s.throttle == pytest.approx(-0.3)


def test_throttle_has_no_float_drift():
    s = make()
    for _ in range(3):
        s.handle('up')
    for _ in range(3):
        s.handle('down')
    assert s.throttle == 0.0


def test_heading_steps_left_positive_and_clamp():
    s = make()
    s.handle('left')
    assert s.heading == pytest.approx(0.1)
    for _ in range(10):
        s.handle('right')
    assert s.heading == pytest.approx(-0.5)
    s.handle('c')
    assert s.heading == 0.0


def test_space_brakes_and_zeroes_throttle():
    s = make()
    s.handle('up')
    assert s.handle(' ') == 'brake'
    assert s.throttle == 0.0


def test_d_disarms_and_zeroes_throttle():
    s = make()
    s.handle('up')
    assert s.handle('d') == 'disarm'
    assert s.throttle == 0.0


def test_arm_requires_zero_throttle():
    s = make()
    s.handle('up')
    assert s.handle('a') == 'arm_refused'
    s.handle('down')
    assert s.handle('a') == 'arm'


def test_quit_and_shutdown():
    s = make()
    s.handle('up')
    assert s.handle('q') == 'quit'
    assert s.throttle == 0.0
    assert s.handle('x') == 'shutdown'
    assert s.handle('Q') == 'quit'


def test_unknown_key_is_noop():
    s = make()
    assert s.handle('z') is None
    assert (s.throttle, s.heading) == (0.0, 0.0)
