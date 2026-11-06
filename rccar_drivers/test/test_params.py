"""Parameter coercion + validation (pure)."""
import pytest

from rccar_drivers.slamtec.params import check_params

D = {'host': 'h', 'port': 1445, 'timeout_s': 1.0, 'scan_rate_hz': 10.0,
     'imu_rate_hz': 50.0, 'pose_rate_hz': 10.0, 'map_period_s': 2.0,
     'health_period_s': 1.0, 'reconnect_max_s': 5.0, 'map_max_cells': 4_000_000,
     'n_bins': 1080, 'range_min': 0.15, 'range_max': 40.0, 'publish_tf': True,
     'imu_trust_acc': False}


def test_defaults_valid():
    cfg, errors = check_params(D, D)
    assert errors == [] and cfg == D


def test_int_for_double_is_cast():
    cfg, errors = check_params(dict(D, range_max=40, scan_rate_hz=20), D)
    assert errors == []
    assert cfg['range_max'] == 40.0 and isinstance(cfg['range_max'], float)
    assert isinstance(cfg['scan_rate_hz'], float)


@pytest.mark.parametrize('key', ['timeout_s', 'scan_rate_hz', 'imu_rate_hz', 'pose_rate_hz',
                                 'map_period_s', 'health_period_s', 'reconnect_max_s',
                                 'map_max_cells'])
@pytest.mark.parametrize('bad', [0, -1.0])
def test_rates_must_be_positive(key, bad):
    _, errors = check_params(dict(D, **{key: bad}), D)
    assert any(key in e for e in errors)


def test_n_bins_minimum():
    assert check_params(dict(D, n_bins=89), D)[1]
    assert check_params(dict(D, n_bins=90), D)[1] == []


def test_range_order():
    assert check_params(dict(D, range_min=40.0), D)[1]
    assert check_params(dict(D, range_min=-1.0), D)[1]


def test_wrong_types_rejected():
    assert check_params(dict(D, publish_tf='yes'), D)[1]
    assert check_params(dict(D, n_bins=10.5), D)[1]
    assert check_params(dict(D, host=5), D)[1]
    assert check_params(dict(D, scan_rate_hz=True), D)[1]


def test_imu_trust_acc_is_bool():
    assert check_params(dict(D, imu_trust_acc=True), D)[0]['imu_trust_acc'] is True
    assert check_params(dict(D, imu_trust_acc=1), D)[1]
