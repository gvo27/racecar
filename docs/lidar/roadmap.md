# Lidar roadmap: what the 2D lidar can do, and what comes next

Source: the roadmap comment on PR #6. Status of the lidar: [README.md](README.md).

## A walled track is necessary

The Slamtec Mapper sees only what crosses one horizontal plane at its scan height. Track boundaries must be physical barriers that are taller than that plane plus a tilt margin, about 30 cm or more. Boards, cardboard, foam or HVAC duct are examples (as on F1TENTH tracks). Floor tape and paint are invisible to the lidar. Cones show only as sparse points with gaps.

Decide early if a walled track (or a space with walls or corridors) is possible. The decision changes the sensor plan.

- The scan plane is near the top of the Mapper. The estimate is 5 to 7 cm above its base (from the 75 mm height in the datasheet), plus the mounting deck. On the TT-02 this is probably 15 to 25 cm above the floor. Measure it during the mount-offset step.
- The plane tilts when the car pitches during acceleration and braking. The Mapper SLAM is rated for ±3° tilt only.

| Tilt | Plane moves at 1 m | at 3 m | at 5 m |
| --- | --- | --- | --- |
| 1° | 1.7 cm | 5 cm | 9 cm |
| 3° | 5 cm | 16 cm | 26 cm |

- Mount the lidar as low and as level as possible. Make the barriers clearly taller than the plane at the distances that are important. A high mount also raises the center of gravity. The Mapper is 75 mm tall, and its mass is reportedly about 500 g (not verified).

| Boundary type | Visible to the 2D lidar |
| --- | --- |
| Walls or barriers (about 30 cm or more) | Yes. F1TENTH algorithms assume this |
| Traffic cones | Partly. Only if taller than the plane. The code must join sparse points into a boundary |
| Floor tape or paint | No. It needs the camera |

If a walled track is not possible, the camera must be the primary boundary sensor for tape lines ("camera-first"). The lidar then gives obstacles and localization against the room walls.

## 3D lidar: not now

- F1TENTH gym (the sim) is 2D. Most F1TENTH work uses a 2D lidar (for example [TinyLidarNet](https://arxiv.org/html/2410.07447v1)).
- The camera solves tape lines and semantics. A 3D lidar adds cost, mass, power and Pi CPU load.
- A 3D lidar is useful for curbs, low obstacles, tilt tolerance, outdoor tracks without walls, or 3D semantic maps. Options:

| Sensor | FOV | Price | Notes |
| --- | --- | --- | --- |
| Livox Mid-360 | 360° x 59° | about $749 at launch | best documented: [TUM open-source 3D SLAM/localization for F1TENTH](https://mos.ed.tum.de/en/avs/news/article/neue-open-source-software-3d-lidar-slam-und-localization-fuer-f1tenth), [F1TENTH Mid-360 build notes](https://thejourneyofbabo.github.io/My-Notes/F1Tenth-Build-3-(3D-LiDAR---MID360)) |
| Unitree L2 | 360° x 90°, built-in IMU | $419 ([Unitree](https://www.unitree.com/L2)) | budget. No F1TENTH integration found |
| Ouster OS0/OS1 | high-resolution 360° | premium | research grade |

- For racing, a low-mounted, fast 2D lidar can be a better upgrade. The Mapper gives raw scans at 10 Hz, and its SLAM is rated to 2 m/s. The F1TENTH rules name 40 Hz units, for example the Hokuyo UTM-30LX ([rules](https://www.ucsg.edu.ec/wp-content/uploads/images/roboracer/F1TENTHRules.pdf)). The Mapper then stays as the mapping and SLAM reference.

## Odometry is the bottleneck, not the camera

The Mapper pose is 10 Hz, about 100 ms late, and it can jump at relocalization. Its IMU gives orientation only (firmware 2.6.0_dev). Recommended order:

1. Finish the lidar bench checks ([README.md](README.md) "Open items").
2. Shaft encoder on the ESP32 (GPIO15/16, pins already reserved, PCNT): closed-loop speed control and wheel odometry.
3. IMU (100 Hz or more): true yaw rate. Fuse it with the encoder in `robot_localization` (EKF) for a smooth `odom→base_link`. The Mapper pose then corrects drift through `map→odom`. This removes the REP-105 shortcut that the driver uses now.
4. Captain node: drive commands through the supervisor on `/rccar/cmd/captain`. First behavior: follow-the-gap or wall following from `/rccar/lidar/scan`. Develop it in F1TENTH gym, then on the car at walking speed, on the walled track.
5. Saved map, localization, racing line with pure pursuit.
6. Camera: put the detections on the 2D map with lidar ranges. This gives a 2D semantic map, the realistic form of semantic SLAM with this hardware. A 2D lidar alone gives geometry, not semantics.

Steps 4 and 5 can start in simulation, in parallel with steps 2 and 3 (the sim is in a separate repo).

## Simulation

- F1TENTH gym: the best fit. Match the real sensor, or policies do not transfer: about 10 Hz scans, about 920 beams over 360°, 40 m range, about 100 ms pose latency, low speed. Model the track with walls (see above).
- Gazebo (sim adapter): a 2D lidar with the same topics and frames. Publish `/rccar/mapper/pose` from ground truth with noise and delay. The onboard SLAM of the Mapper cannot be simulated.
- Isaac Sim: mainly useful for the camera (synthetic labeled images). Wait until the camera arrives.
