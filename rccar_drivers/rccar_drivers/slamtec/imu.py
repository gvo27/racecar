"""
Imu message content from an ImuSample (no rclpy).

Bench (Mapper M2M1, firmware 2.6.0_dev): only the orientation is a real
measurement; rates are not exported, and `acc` (~0.003 at rest, no gravity)
looks gravity-removed with unverified units. Values are always copied raw;
the covariance marks what a consumer may use (REP-145: covariance[0] = -1 means
"not provided", all-zero means "unknown but provided").
"""
from rccar_drivers.slamtec.protocol import ImuBit

NOT_PROVIDED = -1.0


def _cov(provided):
    cov = [0.0] * 9
    if not provided:
        cov[0] = NOT_PROVIDED
    return cov


def imu_fields(sample, trust_acc):
    """
    Return a dict of Imu fields for a protocol.ImuSample.

    orientation (w, x, y, z), angular_velocity, linear_acceleration (tuples)
    and the three 9-element covariance lists. orientation is provided iff the
    QUATERNION bit is set, angular velocity iff CALIBRATED_GYRO, linear
    acceleration iff CALIBRATED_ACC and trust_acc (parameter imu_trust_acc,
    default False: semantics and units are unverified).
    """
    return {
        'orientation': tuple(sample.quat),
        'orientation_covariance': _cov(sample.has(ImuBit.QUATERNION_READY)),
        'angular_velocity': tuple(sample.gyro),
        'angular_velocity_covariance': _cov(sample.has(ImuBit.CALIBRATED_GYRO_READY)),
        'linear_acceleration': tuple(sample.acc),
        'linear_acceleration_covariance': _cov(
            bool(trust_acc) and sample.has(ImuBit.CALIBRATED_ACC_READY)),
    }
