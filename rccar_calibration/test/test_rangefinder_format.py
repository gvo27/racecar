"""Pure rangefinder formatting + rate estimator."""
import math

from rccar_calibration import rangefinder_format as f


def line(rng, sec=1730300000, nsec=123456789, recv=1730300000.130, **kw):
    return f.format_line(sec, nsec, recv, rng, 0.05, 10.0, **kw)


def test_normal_line():
    out = line(1.234)
    assert out.startswith('mcu 1730300000.123456789  pi 1730300000.130  ')
    assert 'range 1.234 m (123.4 cm)' in out
    assert 'out of range' not in out


def test_latency_ms():
    assert 'latency 6.5 ms' in line(1.0)


def test_unsynced_has_no_latency():
    out = line(1.0, sec=0, nsec=0)
    assert 'mcu unsynced' in out
    assert 'latency' not in out


def test_no_return_inf():
    assert 'no return' in line(math.inf)


def test_too_close_neg_inf():
    assert 'too close (-inf)' in line(-math.inf)


def test_nan():
    assert 'invalid' in line(math.nan)


def test_out_of_range():
    assert 'out of range' in line(12.0)
    assert 'out of range' in line(0.01)
    assert 'out of range' not in line(0.05)


def test_rate_in_line():
    assert '49.5 Hz' in line(1.0, rate_hz=49.5)


def test_rate_estimator():
    r = f.RateEstimator(2.0)
    assert r.rate() == 0.0
    for i in range(11):
        r.add(i * 0.1)
    assert abs(r.rate() - 10.0) < 1e-9


def test_rate_estimator_window_drops_old():
    r = f.RateEstimator(1.0)
    for i in range(5):
        r.add(i * 0.5)
    assert abs(r.rate() - 2.0) < 1e-9
    assert r.rate(now=100.0) == 0.0


def test_header_mentions_columns():
    assert 'mcu' in f.HEADER and 'pi' in f.HEADER and 'range' in f.HEADER
