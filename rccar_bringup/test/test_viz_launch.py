"""
launch_testing: viz.launch.py starts foxglove_bridge and opens its websocket port.

Skipped automatically where ROS 2 / launch_testing / foxglove_bridge are missing.
"""
import os
import socket
import time
import unittest

import pytest

pytest.importorskip('launch_testing')
pytest.importorskip('rclpy')

import launch  # noqa: E402,I100,I201,I202
from launch.actions import IncludeLaunchDescription  # noqa: E402,I100,I201,I202
from launch.launch_description_sources import (  # noqa: E402,I100,I201,I202
    PythonLaunchDescriptionSource)
import launch_testing  # noqa: E402,I100,I201,I202
import launch_testing.actions  # noqa: E402,I100,I201,I202


def _have_bridge():
    try:
        from ament_index_python.packages import get_package_prefix
        get_package_prefix('foxglove_bridge')
        return True
    except Exception:
        return False


# no module-level skip: it hides every other test of the package from colcon's pytest run
HAVE_BRIDGE = _have_bridge()

HERE = os.path.dirname(os.path.abspath(__file__))
LAUNCH = os.path.join(HERE, '..', 'launch', 'viz.launch.py')
PORT = 18765


@pytest.mark.launch_test
def generate_test_description():
    if not HAVE_BRIDGE:
        return launch.LaunchDescription([launch_testing.actions.ReadyToTest()])
    return launch.LaunchDescription([
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(LAUNCH),
            launch_arguments={'port': str(PORT)}.items()),
        launch_testing.actions.ReadyToTest(),
    ])


@unittest.skipUnless(HAVE_BRIDGE, 'foxglove_bridge not installed (rosdep installs it in CI)')
class TestViz(unittest.TestCase):
    """The bridge listens on localhost."""

    def test_port_opens(self):
        end = time.monotonic() + 20.0
        err = None
        while time.monotonic() < end:
            try:
                with socket.create_connection(('127.0.0.1', PORT), timeout=1.0):
                    return
            except OSError as exc:
                err = exc
                time.sleep(0.2)
        self.fail(f'foxglove_bridge did not open 127.0.0.1:{PORT}: {err}')
