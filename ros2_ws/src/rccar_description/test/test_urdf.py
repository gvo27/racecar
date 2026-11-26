"""The xacro expands to a URDF with the three frames and fixed joints."""
import os
import xml.etree.ElementTree as ET

import pytest

xacro = pytest.importorskip('xacro')

HERE = os.path.dirname(os.path.abspath(__file__))
FILE = os.path.join(HERE, '..', 'urdf', 'rccar.urdf.xacro')


def test_frames_and_joints():
    root = ET.fromstring(xacro.process_file(FILE).toxml())
    links = {e.get('name') for e in root.findall('link')}
    assert links == {'base_link', 'lidar_link', 'lidar_imu_link'}
    joints = {j.find('child').get('link'): j.get('type') for j in root.findall('joint')}
    assert joints == {'lidar_link': 'fixed', 'lidar_imu_link': 'fixed'}
