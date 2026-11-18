"""docs/sensor_contract.md "active" rows == the topics, types, frames and QoS in the source code."""
from pathlib import Path
import re

import pytest

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / 'docs' / 'sensor_contract.md'
MAPPER = ROOT / 'rccar_drivers' / 'rccar_drivers' / 'mapper_node.py'
FIRMWARE = ROOT / 'firmware' / 'esp32' / 'src' / 'main.cpp'
SUPERVISOR = ROOT / 'rccar_supervisor' / 'rccar_supervisor' / 'supervisor_node.py'
ARBITER = ROOT / 'rccar_supervisor' / 'rccar_supervisor' / 'arbiter.py'
URDF = ROOT / 'rccar_description' / 'urdf' / 'rccar.urdf.xacro'

COLUMNS = ['topic', 'type', 'frame', 'publisher', 'qos', 'rate', 'status', 'sim source']


def contract_rows():
    """Rows of the first table whose header is COLUMNS."""
    rows, in_table = [], False
    for line in CONTRACT.read_text().splitlines():
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if cells == COLUMNS:
            in_table = True
            continue
        if in_table:
            if not line.startswith('|'):
                break
            if set(line) <= set('|- '):
                continue
            rows.append(dict(zip(COLUMNS, cells)))
    return rows


ROWS = contract_rows()
ACTIVE = [r for r in ROWS if r['status'] == 'active']


def by_publisher(name):
    return [r for r in ACTIVE if r['publisher'] == name]


def mapper_defaults():
    """PARAMS dict literal of mapper_node.py, without importing rclpy."""
    src = MAPPER.read_text()
    body = src[src.index('PARAMS = {'):]
    body = body[:body.index('\n}\n') + 2]
    return dict(re.findall(r"'(\w+)':\s*'([^']*)'", body))


def test_contract_parses():
    assert ROWS, 'no topic table in docs/sensor_contract.md'
    assert {r['status'] for r in ROWS} <= {'active', 'planned'}
    assert len({r['topic'] for r in ROWS}) == len(ROWS), 'duplicate topic rows'


@pytest.mark.parametrize('row', by_publisher('mapper_driver'), ids=lambda r: r['topic'])
def test_mapper_driver_rows(row):
    src = MAPPER.read_text()
    msg = row['type'].split('/')[-1]
    m = re.search(r"(\w+),\s*'%s',\s*(\w+)\)" % re.escape(row['topic']), src)
    assert m, '%s not created in mapper_node.py' % row['topic']
    assert m.group(1) == msg, '%s type %s != %s' % (row['topic'], m.group(1), msg)
    qos = {'sensor_data': 'qos_profile_sensor_data', 'reliable+tl': 'MAP_QOS'}[row['qos']]
    assert m.group(2) == qos
    frames = {v for k, v in mapper_defaults().items() if k.endswith('_frame')}
    assert row['frame'] in frames, '%s frame %s not a mapper_node default' % (
        row['topic'], row['frame'])


@pytest.mark.parametrize('row', by_publisher('esp32') + by_publisher('esp32 (service)'),
                         ids=lambda r: r['topic'])
def test_esp32_rows(row):
    """The firmware comms header lists each entity: '//   pub  <topic> <pkg>/msg/<Type>  <qos>'."""
    src = FIRMWARE.read_text()
    kind = 'srv' if row['qos'] == 'service' else 'pub'
    pkg, name = row['type'].split('/')
    sub = 'srv' if kind == 'srv' else 'msg'
    m = re.search(r'//\s+%s\s+%s\s+%s/%s/%s\s+(.*)' % (
        kind, re.escape(row['topic']), pkg, sub, name), src)
    assert m, '%s %s not in the main.cpp comms header' % (kind, row['topic'])
    if kind == 'pub':
        want = 'best effort' if row['qos'] == 'best_effort' else 'reliable'
        assert m.group(1).startswith(want), '%s qos: %s' % (row['topic'], m.group(1))
    if row['frame'] != '-':
        assert 'strcpy(g_rangeFrameBuf, "%s")' % row['frame'] in src


def test_supervisor_is_drive_publisher():
    drive = [r for r in ACTIVE if r['topic'] == '/rccar/mcu/drive']
    assert drive and drive[0]['publisher'] == 'supervisor'
    assert "MCU_DRIVE = '/rccar/mcu/drive'" in SUPERVISOR.read_text()
    src = FIRMWARE.read_text()
    assert re.search(r'//\s+sub\s+/rccar/mcu/drive\s+rccar_msgs/msg/DriveCmd', src)


def test_command_input_topics():
    src = ARBITER.read_text()
    for r in ACTIVE:
        if r['topic'].startswith('/rccar/cmd/'):
            assert "'%s'" % r['topic'] in src, '%s not an arbiter input' % r['topic']


def test_urdf_has_active_sensor_frames():
    """Every active sensor frame is in the URDF, except the gaps listed in the TF table."""
    urdf = URDF.read_text()
    text = CONTRACT.read_text()
    gaps = set(re.findall(r'\| base_link -> (\w+) \| - \| gap \|', text))
    for r in ACTIVE:
        frame = r['frame']
        if frame in ('-', 'map', 'odom') or frame in gaps:
            continue
        assert '<link name="%s"/>' % frame in urdf, 'frame %s missing in URDF' % frame
