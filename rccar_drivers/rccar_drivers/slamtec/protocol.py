"""
Slamtec Mapper M2M1 wire protocol (JSON over TCP 1445), no rclpy.

Source: docs/datasheets/slamtec_mapper_M2M1_datasheet.md section 11.

Unit notes: IMU acc units are undocumented; values are kept raw here. Bench
must confirm m/s^2 vs g before the node scales them.
"""
import base64
from dataclasses import dataclass, field
import json
import math
import socket
import struct

DELIM = b'\n\r\n\r\n'
MAX_REQUEST_ID = 99_999_999


class MapperError(Exception):
    """Protocol or device error."""


class MapperTimeout(MapperError):
    """No (matching) response within the socket timeout."""


class MapperClient:
    """Synchronous request/response client; any error closes the socket."""

    def __init__(self, host, port=1445, timeout_s=1.0,
                 sock_factory=socket.create_connection):
        self._host = host
        self._port = port
        self._timeout_s = timeout_s
        self._factory = sock_factory
        self._sock = None
        self._buf = b''
        self._next_id = 0

    @property
    def connected(self):
        """Return True while a socket is open."""
        return self._sock is not None

    def connect(self):
        """Open the TCP connection (no-op if already open)."""
        if self._sock is not None:
            return
        try:
            self._sock = self._factory((self._host, self._port), self._timeout_s)
        except socket.timeout as e:
            raise MapperTimeout('connect timeout') from e
        except OSError as e:
            raise MapperError('connect failed: %s' % e) from e
        self._sock.settimeout(self._timeout_s)
        self._buf = b''

    def close(self):
        """Close the socket and drop buffered bytes."""
        sock, self._sock = self._sock, None
        self._buf = b''
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass

    def _new_id(self):
        self._next_id = self._next_id % MAX_REQUEST_ID + 1
        return self._next_id

    def _read_message(self):
        while DELIM not in self._buf:
            chunk = self._sock.recv(65536)
            if not chunk:
                raise MapperError('connection closed')
            self._buf += chunk
        msg, self._buf = self._buf.split(DELIM, 1)
        return msg

    def call(self, command, args=None):
        """Send a command and return the response `result` dict."""
        if self._sock is None:
            raise MapperError('not connected')
        rid = self._new_id()
        req = {'command': command, 'request_id': rid}
        if args is not None:
            req['args'] = args
        try:
            self._sock.sendall(json.dumps(req).encode() + DELIM)
            while True:
                raw = self._read_message()
                try:
                    resp = json.loads(raw)
                except ValueError as e:
                    raise MapperError('bad json: %s' % e) from e
                if not isinstance(resp, dict) or resp.get('request_id') != rid:
                    continue  # stale answer to an earlier (timed out) request
                result = resp.get('result')
                if not isinstance(result, dict):
                    raise MapperError('%s: no result' % command)
                code = result.get('code', 0)
                if code != 0:
                    raise MapperError('%s failed: code %s' % (command, code))
                return result
        except socket.timeout as e:
            self.close()
            raise MapperTimeout('%s timed out' % command) from e
        except MapperError:
            self.close()
            raise
        except OSError as e:
            self.close()
            raise MapperError('%s: %s' % (command, e)) from e


def rle_inflate(b64):
    """Base64-decode (padding optional) then undo the device RLE."""
    d = base64.b64decode(b64 + '=' * (-len(b64) % 4))
    if len(d) < 9 or d[:3] != b'RLE':
        raise MapperError('payload header is not RLE')
    s1, s2 = d[3], d[4]
    n = struct.unpack_from('<I', d, 5)[0]
    out, i = bytearray(), 9
    while i < len(d) and len(out) < n:
        if d[i] == s1 and i + 2 < len(d):
            cnt, val = d[i + 1], d[i + 2]
            if cnt == 0 and val == s2:
                s1, s2 = s2, s1
            else:
                out += bytes([val]) * cnt
            i += 3
        else:
            out.append(d[i])
            i += 1
    return bytes(out)


def parse_scan(b64):
    """Return sorted (angle_rad, dist_m, valid) tuples (opensw backwards parser)."""
    d = rle_inflate(b64)
    pts, i, recover = [], len(d) - 1, False
    while i >= 8:
        start = i
        ok = d[i] <= 1
        if ok:
            ang = struct.unpack_from('<f', d, i - 4)[0]
            ok = (math.isfinite(ang) and abs(ang) <= math.pi + 0.01
                  and not (ang != 0 and abs(ang) < 1e-4))
        if ok:
            dist = struct.unpack_from('<f', d, i - 8)[0]
            ok = math.isfinite(dist) and (dist == 100000 or 0.001 < dist <= 100.0)
        if not ok:
            i = min(start + 2, len(d) - 1) if not recover else start - 1
            recover = True
            continue
        pts.append((ang, dist, d[start] == 1))
        recover = False
        i = start - 12
    return sorted(pts)


@dataclass
class MapData:
    """Decoded getmapdata result (cells are raw uint8, row-major assumed)."""

    width: int
    height: int
    resolution: float
    origin_x: float
    origin_y: float
    cells: bytes = field(repr=False, default=b'')


def decode_map(result):
    """Build MapData from a getmapdata result, validating the cell count."""
    try:
        width = int(result['dimension_x'])
        height = int(result['dimension_y'])
        cells = rle_inflate(result['map_data'])
        res = float(result['resolution'])
        ox = float(result.get('real_x', 0.0))
        oy = float(result.get('real_y', 0.0))
    except (KeyError, TypeError, ValueError) as e:
        raise MapperError('bad map result: %r' % (e,)) from e
    if width < 0 or height < 0 or len(cells) < width * height:
        raise MapperError('map has %d cells, need %d x %d'
                          % (len(cells), width, height))
    return MapData(width, height, res, ox, oy, cells)


def _f(d, key, default=0.0):
    try:
        return float(d.get(key, default))
    except (TypeError, ValueError):
        return default


def _xyz(d, key):
    sub = d.get(key) or {}
    return (_f(sub, 'x'), _f(sub, 'y'), _f(sub, 'z'))


@dataclass
class Pose:
    """SLAM pose (m, rad)."""

    x: float = 0.0
    y: float = 0.0
    yaw: float = 0.0
    pitch: float = 0.0
    roll: float = 0.0

    @classmethod
    def from_result(cls, r):
        """Build from a getpose result."""
        return cls(_f(r, 'x'), _f(r, 'y'), _f(r, 'yaw'), _f(r, 'pitch'),
                   _f(r, 'roll'))


@dataclass
class ImuSample:
    """IMU in robot coordinates; units raw (see module docstring)."""

    acc: tuple = (0.0, 0.0, 0.0)
    gyro: tuple = (0.0, 0.0, 0.0)
    quat: tuple = (1.0, 0.0, 0.0, 0.0)  # w, x, y, z

    @classmethod
    def from_result(cls, r):
        """Build from a getimuinrobotcoordinate result."""
        q = r.get('quaternion') or {}
        quat = (_f(q, 'w', 1.0), _f(q, 'x'), _f(q, 'y'), _f(q, 'z'))
        return cls(_xyz(r, 'acc'), _xyz(r, 'gyro'), quat)


@dataclass
class Health:
    """getrobothealth flags."""

    has_error: bool = False
    has_warning: bool = False
    has_fatal: bool = False
    has_lidar_disconnected: bool = False
    has_sdp_disconnected: bool = False
    has_depth_camera_disconnected: bool = False
    has_system_emergency_stop: bool = False

    @classmethod
    def from_result(cls, r):
        """Build from a getrobothealth result."""
        return cls(**{k: bool(r.get(k, False)) for k in cls.__dataclass_fields__})
