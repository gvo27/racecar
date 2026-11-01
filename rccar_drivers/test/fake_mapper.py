"""
Fake Slamtec Mapper TCP server for tests (stdlib only).

Usage: `from fake_mapper import FakeMapper` with the test dir on sys.path.
"""
import base64
import json
import socket
import struct
import threading

DELIM = b'\n\r\n\r\n'


def rle_deflate(data, s1=0x81, s2=0x7F):
    """Encode bytes to the device's RLE, base64 without padding."""
    out = bytearray(b'RLE') + bytes([s1, s2]) + struct.pack('<I', len(data))
    i = 0
    while i < len(data):
        b = data[i]
        n = 1
        while i + n < len(data) and data[i + n] == b and n < 255:
            n += 1
        if n >= 4 or b == s1:
            out += bytes([s1, n, b])
        else:
            out += bytes([b]) * n
        i += n
    return base64.b64encode(bytes(out)).decode().rstrip('=')


def encode_scan(points):
    """Encode (angle, dist, valid) tuples as 12-byte records, RLE+base64."""
    raw = b''.join(struct.pack('<ffB3x', d, a, 1 if v else 0)
                   for a, d, v in points)
    return rle_deflate(raw)


DEFAULT_POINTS = [(-1.0, 2.0, True), (0.0, 3.0, True), (1.0, 100000.0, True),
                  (2.0, 1.5, False)]
MAP_W, MAP_H = 4, 3
MAP_CELLS = bytes([0, 0, 255, 255, 1, 1, 0, 200, 0, 5, 128, 0])


def default_results():
    """Return canned results keyed by command."""
    return {
        'getsdpversion': {'sdp_version': 'fake-1.0'},
        'getlaserscan': {'x': 0.0, 'y': 0.0, 'yaw': 0.0,
                         'laser_points': encode_scan(DEFAULT_POINTS)},
        'getpose': {'x': 1.0, 'y': 2.0, 'yaw': 0.5, 'pitch': 0.0, 'roll': 0.0},
        'getimuinrobotcoordinate': {
            'acc': {'x': 0.1, 'y': 0.2, 'z': 9.8},
            'gyro': {'x': 0.0, 'y': 0.0, 'z': 0.3},
            'quaternion': {'w': 1.0, 'x': 0.0, 'y': 0.0, 'z': 0.0}},
        'getknownarea': {'min_x': -1.0, 'min_y': -1.0, 'max_x': 1.0, 'max_y': 1.0},
        'getmapdata': {'dimension_x': MAP_W, 'dimension_y': MAP_H,
                       'size': MAP_W * MAP_H, 'resolution': 0.05,
                       'real_x': -1.0, 'real_y': -1.0,
                       'map_data': rle_deflate(MAP_CELLS)},
        'getrobothealth': {'has_error': False, 'has_warning': False,
                           'has_fatal': False, 'has_lidar_disconnected': False},
        'getsystemresource': {'battery_percentage': 100,
                              'board_temperature10': 400},
    }


class FakeMapper:
    """Threaded TCP server speaking the Mapper protocol on 127.0.0.1."""

    def __init__(self, results=None, chunk=None, stale_first=False):
        """
        Create the server.

        chunk: if set, responses are sent in pieces of this many bytes.
        stale_first: send a response with a wrong request_id before each real one.
        """
        self.results = default_results()
        if results:
            self.results.update(results)
        self.chunk = chunk
        self.stale_first = stale_first
        self.silent = False  # when True, requests are read but never answered
        self.requests = []
        self._lock = threading.Lock()
        self._conns = []
        self._stop = threading.Event()
        self._srv = socket.socket()
        self._srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._srv.bind(('127.0.0.1', 0))
        self._srv.listen(4)
        self._srv.settimeout(0.1)
        self.port = self._srv.getsockname()[1]
        self._thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._thread.start()

    def _accept_loop(self):
        while not self._stop.is_set():
            try:
                conn, _ = self._srv.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            with self._lock:
                self._conns.append(conn)
            threading.Thread(target=self._serve, args=(conn,), daemon=True).start()

    def _send(self, conn, payload):
        if self.chunk:
            for i in range(0, len(payload), self.chunk):
                conn.sendall(payload[i:i + self.chunk])
        else:
            conn.sendall(payload)

    def _serve(self, conn):
        buf = b''
        try:
            while not self._stop.is_set():
                data = conn.recv(65536)
                if not data:
                    return
                buf += data
                while DELIM in buf:
                    raw, buf = buf.split(DELIM, 1)
                    self._handle(conn, json.loads(raw))
        except OSError:
            return

    def _handle(self, conn, req):
        self.requests.append(req)
        if self.silent:
            return
        cmd, rid = req['command'], req['request_id']
        if cmd in self.results:
            result = dict(self.results[cmd], code=0)
        else:
            result = {'code': 1}
        out = b''
        if self.stale_first:
            out += json.dumps({'command': cmd, 'request_id': rid + 1000,
                               'result': {'code': 0, 'stale': True}}).encode() + DELIM
        out += json.dumps({'command': cmd, 'request_id': rid,
                           'result': result}).encode() + DELIM
        self._send(conn, out)

    def drop_connections(self):
        """Close every client connection (simulates link loss)."""
        with self._lock:
            conns, self._conns = self._conns, []
        for c in conns:
            try:
                c.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            c.close()

    def stop(self):
        """Stop the server and close all connections."""
        self._stop.set()
        self.drop_connections()
        self._srv.close()
        self._thread.join(timeout=2.0)
