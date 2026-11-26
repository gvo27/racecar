"""ASCII command builders for the typed services."""
import pytest

from rccar_mcu_bridge import commands as c


def test_set_param():
    assert c.set_param_cmd('gain', 1.5) == 'SET gain 1.5'
    assert c.set_param_cmd('timeout', 300.0) == 'SET timeout 300'


@pytest.mark.parametrize('key', ['', 'a b', 'x\nARM', 'gain;ARM', 'k' * 40])
def test_set_param_rejects_bad_keys(key):
    with pytest.raises(ValueError):
        c.set_param_cmd(key, 1.0)


@pytest.mark.parametrize('value', [float('nan'), float('inf')])
def test_set_param_rejects_nonfinite(value):
    with pytest.raises(ValueError):
        c.set_param_cmd('gain', value)


def test_cal_point():
    assert c.cal_point_cmd(0, 1200) == 'CAL LEFT 1200'
    assert c.cal_point_cmd(1, 1500) == 'CAL CENTER 1500'
    assert c.cal_point_cmd(2, 1800) == 'CAL RIGHT 1800'
    with pytest.raises(ValueError):
        c.cal_point_cmd(3, 1500)


def test_raw_pwm():
    assert c.raw_pwm_cmd(1500) == 'RAW 1500'
    assert c.raw_pwm_cmd(-1) == 'RAW OFF'
    with pytest.raises(ValueError):
        c.raw_pwm_cmd(100)
    with pytest.raises(ValueError):
        c.raw_pwm_cmd(3000)


def test_never_arms():
    assert not any(cmd.startswith('ARM') for cmd in (
        c.set_param_cmd('gain', 1), c.cal_point_cmd(1, 1500), c.raw_pwm_cmd(-1)))
