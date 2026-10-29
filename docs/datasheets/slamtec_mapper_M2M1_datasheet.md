# SLAMTEC Mapper Pro — Model M2M1 — Consolidated Datasheet (LLM context)

> Distilled from: SLAMTEC Mapper M2M1 datasheet rev 1.1 (2019‑11‑29), SLAMTEC Mapper quick‑start (M1M1/M2M3),
> RPLIDAR S1 user manual v1.1, the open‑source `hatchbed/opensw` + `opensw_ros` drivers, and retailer listings.
> Provenance tags: **[DS]** = official M2M1 datasheet · **[QS]** = official Mapper quick‑start (sister model) ·
> **[S1]** = RPLIDAR S1 manual (internal core, inferred) · **[OSW]** = opensw reverse‑engineered driver ·
> **[RET]** = retailer/third party · **[INF]** = inferred, not documented — verify before relying on it.

## 0. Unit identity
| Field | Value |
|---|---|
| Manufacturer | Shanghai Slamtec Co., Ltd. (brand on lidar cap: "RPLIDAR") |
| Product | SLAMTEC Mapper Pro Kit — Laser Mapping Sensor (SparkFun SKU SEN‑15871) |
| Model | **M2M1** (Pro / industrial; 40 m). Sister models: M1M1 (dev, 20 m), M2M2, M2M3 (later revisions) |
| Label P/N (this unit) | `P.001.00M2M10001` |
| Label S/N (this unit) | `A4EEFA0CE1EEF79A D5E7F4F924435030` |
| Status | Discontinued at several retailers; no firmware updates reported [RET] |

## 1. What it is
- 2D 360° time‑of‑flight lidar **plus** an onboard computer ("Data Processing Unit") running SLAMTEC's SLAMWARE SLAM 3.0 engine with SharpEdge mapping and active loop closure [DS].
- Built‑in 9‑DOF IMU (accelerometer, gyroscope, magnetometer) for tilt compensation, so it can map handheld [DS].
- Output: raw laser scan, real‑time occupancy map, pose (x, y, θ), localization quality [DS]. It needs no external odometry.
- Communicates over **Ethernet or Wi‑Fi using a JSON‑over‑TCP protocol**. The serial protocol of the standalone RPLIDARs (`rplidar`, `pyrplidar`, `rplidar_ros`) does **not** apply to the external ports [OSW].
- Architecture: `[RPLIDAR ranging core (S1‑class)] --UART cable--> [Data Processing Unit: SLAM + IMU + Wi‑Fi/Ethernet] --TCP:1445--> host`.

## 2. Measurement performance [DS]
| Parameter | Value | Note |
|---|---|---|
| Distance range | 40 m | at 92 % reflectivity (white target). The datasheet "Mechanism" text says 20 m (copied from M1M1); the spec table says 40 m |
| Sample rate | 9200 Hz | |
| Scan direction / FOV | clockwise, 360° | |
| Max mapping area | 300 m × 300 m (≈100,000 m²) | |
| Map resolution | 0.05 m / pixel | |
| Accuracy (relocalization) | < 0.02 m | |
| Max linear speed while mapping | 2 m/s | |
| Max angular speed | TBD | |
| Max inclination while mapping | ±3° | |
| Graph‑optimization working time | ~1 h | after that it falls back to non‑graph‑optimized mapping |
| Data / pose refresh | 10 Hz | |
| Map fusion rate | > 10 Hz | |

## 3. Laser [DS]
| Parameter | Min | Typ | Max |
|---|---|---|---|
| Wavelength | 895 nm | 905 nm | 915 nm |
| Peak power (instantaneous) | – | 28 W | – |
| Pulse length | – | 10 ns | – |
| Duty ratio | – | 0.0092 | – |
| Safety class | IEC‑60825 **Class 1** | | |

Modulated pulsed IR rejects ambient light. Works indoors and outdoors, but avoid direct sun into the window.

## 4. Electrical — power [DS]
| Parameter | Min | Typ | Max | Remark |
|---|---|---|---|---|
| Supply voltage | 4.8 V | 5 V | **12 V** | above max may damage the core |
| Ripple | – | 20 mV | 50 mV | high ripple → core failure |
| Startup current | 1400 mA | 1500 mA | 1600 mA | **size the supply for ≥ 1.6 A** |
| Current, 5 V, "power off" (standby) | – | 40 mA | 50 mA | |
| Current, 5 V, running | – | 750 mA | 1300 mA | ≈ 3.75 W typ |
| PoE | IEEE 802.3at Type 2 (Pro kit) | | | |

Kit power cable: 1.5 m, **USB‑A male → 2‑pin wire‑to‑board housing** [DS fig 2‑6]. A USB port must supply ≥ 1.5 A at startup, so use a ≥ 2 A USB charger rather than a PC port.

## 5. Interfaces & pinouts

### 5.1 External connectors (on the Data Processing Unit) [DS fig 2‑5]
| Connector | Function | Notes |
|---|---|---|
| "5V DC" | Power in | 2‑pin wire‑to‑board receptacle that mates with the kit cable. Standard colors: red = +V, black = GND [INF]. 4.8–12 V |
| RJ45 "Ethernet" | 10/100BASE‑TX (802.3/802.3u), PoE 802.3at Type 2 | standard pinout below |
| "Connection" (side) | Internal link to the lidar head | 0.3 m multi‑wire jumper; see 5.3 |
| Wi‑Fi (internal) | 802.11 a/b/g/n/ac, dual‑mode AP/Station | |

### 5.2 RJ45 pinout (standard 10/100, T568B colors) [standard / INF for PoE mode]
| Pin | T568B color | 10/100 signal | PoE Mode A (on data pairs) | PoE Mode B (on spare pairs) |
|---|---|---|---|---|
| 1 | white/orange | TX+ | V+ (or V−) | – |
| 2 | orange | TX− | V+ (or V−) | – |
| 3 | white/green | RX+ | V− (or V+) | – |
| 4 | blue | unused | – | V+ |
| 5 | white/blue | unused | – | V+ |
| 6 | green | RX− | V− (or V+) | – |
| 7 | white/brown | unused | – | V− |
| 8 | brown | unused | – | V− |
Auto‑MDIX support is not documented; use a switch, or a crossover cable if a direct link fails. The datasheet doesn't say which PoE mode (A/B) it uses. A standards‑compliant 802.3at PSE/injector negotiates this automatically.

### 5.3 Internal lidar‑core link (head ↔ processing unit) — [S1] + [INF]
The M2M1's ranging specs match the **RPLIDAR S1** core exactly (40 m, 9200 Hz, 905 nm, Class 1). The 0.3 m jumper in DS fig 2‑6 is a fine‑pitch 6‑wire lead, consistent with the S1's **SH1.0‑6P** (JST‑SH, 1.0 mm pitch) interface. S1 pinout:

| Pin (as drawn, L→R) | Wire color | Signal | Type | Min | Typ | Max |
|---|---|---|---|---|---|---|
| 1 | Blue | TX (core → host) | output, 3.3 V TTL | 0 V | 3.3 V | 3.5 V |
| 2 | Green | RX (host → core) | input, 3.3 V TTL | 0 V | 3.3 V | 3.5 V |
| 3 | Yellow | GND | power | 0 V | 0 V | 0 V |
| 4 | Orange | GND | power | 0 V | 0 V | 0 V |
| 5 | Purple | VCC | power | 4.8 V | 5 V | 5.5 V |
| 6 | Brown | VCC | power | 4.8 V | 5 V | 5.5 V |

- UART: **256000 baud, 8N1**, standard RPLIDAR serial protocol (works with `rplidar_sdk`, `pyrplidar`, and ROS `rplidar_ros` with the `s1` profile) [S1].
- VCC is 5 V **max 5.5 V**. Never feed the 12 V the processing unit accepts into this connector.
- Pin order is read from the S1 manual drawing. Confirm wire colors and continuity with a multimeter before tapping this link. Using it bypasses the onboard SLAM.

## 6. Network defaults
| Item | Value | Source |
|---|---|---|
| Wi‑Fi default mode | AP (hotspot), SSID `SLAMWARE-XXXXXX`, open (no password) | [QS], [RET] |
| Device IP in AP mode | **192.168.11.1** | [QS] |
| Control/data port | **TCP 1445** | [QS], [OSW] |
| Ethernet | PC set as **DHCP client** when cabled directly | [QS] (M1M1) |
| `opensw` default host | 192.168.11.11 | [OSW] (if 192.168.11.1 fails, try this) |
| Station (client) mode | configurable via RoboStudio / SDK | [RET] |
| Boot | spins up ≈ 20 s (M1M1) / ≈ 40 s (M2M3) after power. M1M1 dev kit has power switch SW1 and LED D1 | [QS] |

## 7. Coordinate frame [DS]
- Right‑handed. **+X = sensor front** (the ▷ arrow on the lidar cap points along +X). +Y = left. +Z = up.
- Origin is the ranging core's rotation center.
- Scan angles are radians within [−π, π] [OSW]. Distances are meters.

## 8. Mechanical [DS fig 5‑1, drawing read]
| Item | Value |
|---|---|
| Body footprint | ≈ 57 × 57 mm (56.99) |
| Overall height | 74.90 mm (base 23.91 mm; base + processing unit 43.40 mm) |
| Overall incl. mounting ears | ≈ 57 × 77 × 75 mm [RET] |
| Side mounting ears | 2 × Ø3.20 mm through (M3), 90° countersink Ø6.7, centers **67.11 mm** apart |
| Bottom threaded holes | 2 × M3, 4 mm deep, 24 mm apart (±12 mm from centerline) |
| Bottom countersunk holes | 4 × Ø2.40 through, Ø4.5 × 90° (M2.5) |
| Bottom plate | ≈ 47 × 46 mm |
| ⚠ Screw limit | **The 4 × M2.5 screws in the lidar bottom must be ≤ 6 mm long, or the internal module is damaged** |
| Optical window | keep the emit/receive band on the rotating head unobstructed. Any cover needs SLAMTEC approval |
| Weight | TBD in DS. ~500 g reported [RET, unverified] |

## 9. Environmental [DS]
Operating −5 °C … +45 °C (typ 25 °C). Storage TBD. Pre‑heating improves accuracy (S1 core guidance) [S1].

## 10. Software stack
| Tool | Purpose |
|---|---|
| **RoboStudio** (Windows) | GUI: connect at 192.168.11.1:1445, view map and scan, set Wi‑Fi mode, run firmware tools |
| **SLAMWARE SDK** (C++, closed source; x86 Win/Linux, ARM Linux) | official API |
| **slamware_ros_sdk** (ROS 1) | `roslaunch slamware_ros_sdk slamware_ros_sdk_server_node.launch ip_address:=192.168.11.1` |
| **hatchbed/opensw** (C++, BSD) + **opensw_ros** (ROS 1/2) | open reimplementation. Nodes: `laser_driver` → `scan` (sensor_msgs/LaserScan, frame `laser`, 20 Hz, range 0–40 m); `imu_driver` → `imu` (sensor_msgs/Imu, frame `imu`, 50 Hz). Params: `host`, `port`=1445 |
| SDK health interface | reports faults. Restart the unit to recover [DS] |

## 11. Wire protocol (reverse‑engineered, [OSW])
- **Transport:** TCP to port 1445. Each message is a single JSON object terminated by the delimiter **`"\n\r\n\r\n"`**. Request/response is synchronous and matched by `request_id` (int 1–99999999).
- **Simple request:** `{"command":"<cmd>","request_id":12345}`
- **Response envelope:** `{"command":"<cmd>","request_id":12345,"result":{"code":<int>,"timestamp":<int>, ...}}`

| command | args | result fields |
|---|---|---|
| `getlaserscan` | – | `x`, `y`, `yaw` (sensor pose at scan time), `laser_points` (base64 + RLE, see below) |
| `getpose` | – | `x`, `y` (m), `yaw`, `pitch`, `roll` (rad) |
| `getlocation` | – | `x`, `y` |
| `getimuinrobotcoordinate` | – | `acc{x,y,z}`, `gyro{x,y,z}`, `compass{x,y,z}`, `quaternion{w,x,y,z}`, `raw_acc`, `raw_gyro`, `raw_compass` |
| `getknownarea` | `{"type":int,"kind":int,"partially":bool}` | `min_x`, `min_y`, `max_x`, `max_y` (m) |
| `getmapdata` | `{"area":{"x","y","width","height"},"type":0,"kind":<MapKind>,"partially":false}` | `dimension_x`, `dimension_y`, `size`, `resolution`, `real_x`, `real_y`, `map_data` (base64 + RLE, uint8 per cell) |
| `getrobothealth` | – | `has_error`, `has_warning`, `has_fatal`, `has_lidar_disconnected`, `has_sdp_disconnected`, `has_depth_camera_disconnected`, `has_system_emergency_stop` |
| `getsystemresource` | – | `battery_percentage`, `board_temperature10` (°C × 10), `dcin_connected`, `is_charging`, `on_dock` |
| `getsdpversion` | – | `sdp_version` (firmware string) |

- **MapType:** 0 Bitmap8Bit, 1 Pointmap, 2 ImageFeaturesMap, 3 RectangleAreaMap.
- **MapKind:** 0 EXPLORERMAP, 5 COSTMAP, 10 SWEEPERMAP, 20 UWBMAP, 30 SLAMMAP, 40 LOCALSLAMMAP, 50 DBOWMAP, 60 OPTIMALOPERATIONALMAP, 70 MARKERMAP, 80 RECTANGLEAREAMAP, 90 DISCREPANCYRECORDMAP. Use 0 (explorer) for the live occupancy map.

**Binary payload encoding** (`laser_points`, `map_data`): base64‑decode, then apply custom RLE.
- 9‑byte header: `'R' 'L' 'E'`, sentinel `s1` (usually 0x81), sentinel `s2` (usually 0x7F), then uint32 LE decoded length.
- Body: when a byte equals `s1`, the next two bytes are `count, value`. Emit `value` `count` times. Exception: the sequence `s1, 0x00, s2` means "swap s1 and s2", with nothing emitted. Every other byte is copied literally.
- Decoded laser data: 12 bytes per point, little‑endian: `float32 distance_m`, `float32 angle_rad`, `uint8 valid`, 3 bytes padding. Base64 arrives **without padding**. Decoded scans contain stray bytes, so parse **backwards from the end** in 12‑byte steps and resync on invalid records (as opensw does). `distance == 100000` means no return. Sort points by angle.

### Minimal Python client (stdlib only)
```python
import socket, json, base64, struct, random

DELIM = b"\n\r\n\r\n"

class Mapper:
    def __init__(self, host="192.168.11.1", port=1445, timeout=2.0):
        self.s = socket.create_connection((host, port), timeout=timeout)
        self.buf = b""

    def call(self, command, args=None):
        req = {"command": command, "request_id": random.randint(1, 99_999_999)}
        if args is not None:
            req["args"] = args
        self.s.sendall(json.dumps(req).encode() + DELIM)
        while DELIM not in self.buf:
            chunk = self.s.recv(65536)
            if not chunk:
                raise ConnectionError("closed")
            self.buf += chunk
        msg, self.buf = self.buf.split(DELIM, 1)
        return json.loads(msg)["result"]

def rle_inflate(b64: str) -> bytes:
    d = base64.b64decode(b64 + "=" * (-len(b64) % 4))   # device omits padding
    s1, s2 = d[3], d[4]
    n = struct.unpack_from("<I", d, 5)[0]
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

def parse_scan(b64: str):
    """Port of opensw parseLaserPoints: walk backwards in 12-byte records, resync on bad bytes."""
    import math
    d = rle_inflate(b64)
    pts, i, recover = [], len(d) - 1, False
    while i >= 8:
        start = i
        ok = d[i] <= 1
        if ok:
            ang = struct.unpack_from("<f", d, i - 4)[0]
            ok = math.isfinite(ang) and abs(ang) <= math.pi + 0.01 and not (ang != 0 and abs(ang) < 1e-4)
        if ok:
            dist = struct.unpack_from("<f", d, i - 8)[0]
            ok = math.isfinite(dist) and (dist == 100000 or 0.001 < dist <= 100.0)
        if not ok:
            i = min(start + 2, len(d) - 1) if not recover else start - 1
            recover = True
            continue
        pts.append((ang, dist, d[start] == 1))   # (angle_rad, dist_m, valid)
        recover = False
        i = start - 12
    return sorted(pts)

# m = Mapper()
# r = m.call("getlaserscan");  pts = parse_scan(r["laser_points"])
# pose = m.call("getpose")
# area = m.call("getknownarea", {"type": 0, "kind": 0, "partially": False})
# mp = m.call("getmapdata", {"area": {"x": area["min_x"], "y": area["min_y"],
#        "width": area["max_x"] - area["min_x"], "height": area["max_y"] - area["min_y"]},
#        "type": 0, "kind": 0, "partially": False})
# import numpy as np; grid = np.frombuffer(rle_inflate(mp["map_data"]), np.uint8)  # reshape per dimension_x/y
```
Validated: `parse_scan` reproduces opensw's expected output exactly on all 24 captured M2M1 scans, which have about 915–931 points each (≈ 9200 Hz ÷ 10 Hz). `rle_inflate` decodes the captured 40 × 40 map to its declared `size`. The grid layout is ambiguous: opensw builds `cv::Mat(rows=dimension_x, cols=dimension_y)`. Verify the orientation against RoboStudio.

## 12. Gotchas
1. The external ports don't speak the RPLIDAR serial protocol. Use JSON/TCP (§11), the SLAMWARE SDK, or a ROS driver.
2. Startup draws up to 1.6 A. Weak USB ports cause boot loops.
3. Keep M2.5 bottom screws ≤ 6 mm.
4. After ~1 h of continuous mapping, graph optimization stops. Save the map and restart for large sessions.
5. Mapping tolerates only ±3° of tilt, and speeds up to 2 m/s.
6. The datasheet's 20 m figure is a copy error. The spec table (40 m) is authoritative for M2M1.

## 13. Sources
- M2M1 datasheet rev 1.1: https://cdn.sparkfun.com/assets/0/5/8/f/a/DS-15871-Slamtec_Mapper_Pro.pdf
- Mapper quick start (M1M1): https://cdn.sparkfun.com/assets/a/3/5/7/0/PM-15870-Slamtec_Mapper_Dev.pdf
- Mapper quick start (M2M3): https://gargantua.ai/wp-content/uploads/2025/01/SQ108_SLAMTEC_MAPPER_Kit_usermanual_M2M3_v1.0_en.pdf
- RPLIDAR S1 user manual v1.1: https://cdn.sparkfun.com/assets/f/7/1/4/4/LM601_SLAMTEC_rplidarkit_usermanual_S1_v1.1_en.pdf
- opensw (protocol): https://github.com/hatchbed/opensw · opensw_ros: https://github.com/hatchbed/opensw_ros
- SparkFun product page: https://sparkfun.com/products/15871
- SLAMTEC support/downloads: https://www.slamtec.com/en/support
