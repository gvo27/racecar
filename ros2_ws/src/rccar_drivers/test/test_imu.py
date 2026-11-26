"""Pure tests for slamtec.imu.imu_fields (Imu message content from an ImuSample)."""
from rccar_drivers.slamtec.imu import imu_fields
from rccar_drivers.slamtec.protocol import ImuBit, ImuSample

BENCH = ImuBit.QUATERNION_READY | ImuBit.CALIBRATED_ACC_READY | ImuBit.FUSION_6DOF_READY
NOT_PROVIDED = [-1.0] + [0.0] * 8
UNKNOWN = [0.0] * 9


def sample(avail):
    return ImuSample(acc=(0.003, 0.0, 0.0), gyro=(0.0, 0.0, 0.0),
                     quat=(0.9, 0.0, 0.0, 0.1), avail=avail)


def test_bench_bitmap_default_does_not_trust_acc():
    f = imu_fields(sample(int(BENCH)), trust_acc=False)
    assert f['orientation'] == (0.9, 0.0, 0.0, 0.1)
    assert f['orientation_covariance'] == UNKNOWN
    assert f['angular_velocity_covariance'] == NOT_PROVIDED
    assert f['linear_acceleration_covariance'] == NOT_PROVIDED
    # values are still copied raw
    assert f['linear_acceleration'] == (0.003, 0.0, 0.0)
    assert f['angular_velocity'] == (0.0, 0.0, 0.0)


def test_trust_acc_needs_the_bit():
    assert imu_fields(sample(int(BENCH)), True)['linear_acceleration_covariance'] == UNKNOWN
    no_acc = int(ImuBit.QUATERNION_READY)
    assert imu_fields(sample(no_acc), True)['linear_acceleration_covariance'] == NOT_PROVIDED


def test_gyro_bit_provides_rate():
    avail = int(BENCH | ImuBit.CALIBRATED_GYRO_READY)
    assert imu_fields(sample(avail), False)['angular_velocity_covariance'] == UNKNOWN


def test_no_quaternion_bit_marks_orientation_not_provided():
    f = imu_fields(sample(int(ImuBit.CALIBRATED_ACC_READY)), True)
    assert f['orientation_covariance'] == NOT_PROVIDED


def test_no_bitmap_is_legacy_everything_provided_acc_still_gated():
    f = imu_fields(sample(None), trust_acc=True)
    assert f['orientation_covariance'] == UNKNOWN
    assert f['angular_velocity_covariance'] == UNKNOWN
    assert f['linear_acceleration_covariance'] == UNKNOWN
    assert imu_fields(sample(None), False)['linear_acceleration_covariance'] == NOT_PROVIDED


def test_covariances_are_independent_lists():
    f = imu_fields(sample(None), True)
    f['orientation_covariance'][0] = 5.0
    assert f['angular_velocity_covariance'][0] == 0.0
