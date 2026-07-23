# slam_robot_bringup

ROS2 bringup package for an autonomous SLAM robot on Mecanum wheels.
Target platform: **ROS2 Humble / Ubuntu 22.04**.

This package holds the URDF, launch files and configuration to bring up a small
indoor robot: a YDLIDAR X2 laser scanner feeds `slam_toolbox` for live mapping,
while a text-based serial bridge exchanges velocity commands and odometry with
an Arduino Mega running the low-level motor firmware.

## Architecture

**Hardware.** An Axiomtek CAPA55R mini-PC (Ubuntu 22.04, ROS2 Humble) is the
brain; a YDLIDAR X2 provides 360-degree scans over USB; an Arduino Mega 2560
runs the real-time motor control (PID + odometry) and talks to the PC over a
simple serial link. Drive is four JGB37-520 gearmotors with Hall encoders,
two HW-231 drivers and Mecanum wheels (97 mm diameter).

**Software.** ROS2 nodes run on the CAPA55R: the YDLIDAR driver publishes
`/scan`, `slam_toolbox` builds the map, and the `serial_bridge` node converts
`/cmd_vel` into serial frames for the Arduino and turns the Arduino's odometry
frames back into `/odom` plus the `odom -> base_footprint` transform. Nav2 is
provided as configuration for later autonomous navigation.

| Component | Detail |
|---|---|
| Compute | Axiomtek CAPA55R (Ubuntu 22.04, ROS2 Humble) |
| LiDAR | YDLIDAR X2 (UART/USB, 115200 baud, `/dev/ttyUSB0`) |
| Microcontroller | Arduino Mega 2560, plain-text serial link (`/dev/ttyACM0`, 115200 baud) |
| IMU | MPU-6050 on the Arduino (`/imu/data`, planned) |
| Drive | 4x JGB37-520 + Hall encoders, 2x HW-231 drivers, Mecanum wheels (diameter 97 mm) |

## Layout

```
slam_robot_bringup/
├── launch/
│   ├── lidar.launch.py          # X2 driver + static TF base_link -> laser_frame
│   ├── slam.launch.py           # slam_toolbox online_async (+ optional fake odom TF)
│   ├── robot_base.launch.py     # serial_bridge (Arduino serial bridge, port param)
│   └── full_bringup.launch.py   # URDF + LiDAR + SLAM (toggled by arguments)
├── scripts/
│   └── serial_bridge.py         # ROS2 <-> Arduino serial bridge: /cmd_vel -> serial, serial -> /odom + TF
├── config/
│   ├── ydlidar_x2.yaml          # LiDAR driver parameters
│   ├── slam_params.yaml         # slam_toolbox, tuned for weak/absent odometry
│   └── nav2_params.yaml         # Holonomic Nav2 base (MPPI) for later use
├── urdf/
│   └── slam_robot.urdf.xacro    # base_footprint, base_link, 4 wheels, laser_frame, imu_link
└── README.md
```

Dimensions marked `TODO` in the URDF and in `nav2_params.yaml` (LiDAR height,
robot radius, wheelbase) are placeholders to replace with real measurements.

## Build

```bash
cd ~/ros2_ws
colcon build --packages-select slam_robot_bringup ydlidar_ros2_driver
source install/setup.bash
```

The YDLIDAR driver needs the YDLidar-SDK installed first (see the
`ydlidar_ros2_driver` README).

## Quick start

The steps below assume the LiDAR is plugged in and shows up as `/dev/ttyUSB0`
(check with `ls /dev/ttyUSB*`) and that the user is in the `dialout` group
(`sudo usermod -aG dialout $USER`, then log out and back in).

1. **LiDAR only** — verify scans in RViz (fixed frame `laser_frame`, add
   `LaserScan` on `/scan`):
   ```bash
   ros2 launch slam_robot_bringup lidar.launch.py
   ```

2. **SLAM, robot pushed by hand** — no Arduino connected. The launch publishes
   an identity `odom -> base_footprint` transform and lets scan matching
   estimate all motion. Push the robot slowly.
   ```bash
   ros2 launch slam_robot_bringup slam.launch.py
   ```
   In RViz set fixed frame to `map` and add `Map` (`/map`), `LaserScan` and `TF`.

3. **Full bringup** — URDF + LiDAR + SLAM, each toggleable:
   ```bash
   ros2 launch slam_robot_bringup full_bringup.launch.py
   ros2 launch slam_robot_bringup full_bringup.launch.py use_slam:=false
   ```

4. **Real robot with the Arduino** — start the serial bridge, then start SLAM
   with the fake odometry disabled so the transform is not published twice:
   ```bash
   ros2 launch slam_robot_bringup robot_base.launch.py            # publishes /odom + TF
   ros2 launch slam_robot_bringup slam.launch.py publish_fake_odom:=false
   ```

5. **Save the map** once it looks good:
   ```bash
   mkdir -p ~/maps
   ros2 run nav2_map_server map_saver_cli -f ~/maps/my_map
   ```

Important: whenever `serial_bridge` is running it publishes
`odom -> base_footprint`. Always launch SLAM with `publish_fake_odom:=false` in
that case, otherwise two sources publish the same transform and the map breaks.

## Current status

- Motor control (PID + feedforward) on the Arduino: functional.
- LiDAR acquisition and TF tree (`map -> odom -> base -> laser`): functional.
- SLAM mapping with `slam_toolbox`: functional (real, even approximate,
  odometry from the Arduino is required for scan matching to progress).
- Remote teleoperation over WiFi (SSH + ROS2 `/cmd_vel`): functional.
- Nav2 autonomous navigation: integrated as configuration; MPPI controller
  tuning is still in progress.

## Known issues

- **Nav2 / MPPI tuning is not finished.** Velocity limits and critic weights in
  `nav2_params.yaml` are a reasonable base, not validated on the real robot.
- **Mechanical rigidity.** The chassis is fully 3D-printed; vibrations reach the
  LiDAR while driving. Threaded inserts and stiffer structural parts are needed.
- **Lab WiFi** is occasionally unstable during remote sessions.
- **Lateral (strafe) motion is mechanically limited** by the Mecanum rollers
  rubbing on the current chassis.
- **URDF and Nav2 dimensions** marked `TODO` still need real measurements.

## License

MIT. Maintainer: Ruben Fabioux.
