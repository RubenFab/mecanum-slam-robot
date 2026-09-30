# slam_robot_bringup

ROS2 bringup package for an autonomous SLAM robot on Mecanum wheels, built from scratch during a 7-week internship at **Universiti Teknologi PETRONAS (UTP)**, Malaysia.

Target platform: **ROS2 Humble / Ubuntu 22.04**.

This package holds the URDF, launch files and configuration to bring up a small indoor robot: a YDLIDAR X2 feeds `slam_toolbox` for live mapping, while a text-based serial bridge exchanges velocity commands and odometry with an Arduino Mega running the low-level motor firmware.

## Architecture

**Hardware.** An Axiomtek CAPA55R mini-PC (Ubuntu 22.04, ROS2 Humble) is the brain. A YDLIDAR X2 provides 360-degree scans over USB. An Arduino Mega 2560 runs the real-time motor control (PID + odometry) and talks to the PC over a simple serial link. Drive is four JGB37-520 gearmotors with Hall encoders, two HW-231 drivers and 97 mm Mecanum wheels.

**Software.** ROS2 nodes run on the CAPA55R: the YDLIDAR driver publishes `/scan`, `slam_toolbox` builds the map, and the `serial_bridge` node converts `/cmd_vel` into serial frames for the Arduino and turns the Arduino's odometry frames back into `/odom` plus the `odom -> base_footprint` transform. Nav2 is provided as configuration for later autonomous navigation.

| Component | Detail |
| --- | --- |
| Compute | Axiomtek CAPA55R (Ubuntu 22.04, ROS2 Humble) |
| LiDAR | YDLIDAR X2 (UART/USB, 115200 baud, `/dev/ttyUSB0`) |
| Microcontroller | Arduino Mega 2560, plain-text serial link (`/dev/ttyACM0`, 115200 baud) |
| IMU | MPU-6050 on the Arduino (`/imu/data`, planned) |
| Drive | 4x JGB37-520 + Hall encoders, 2x HW-231 drivers, Mecanum wheels (97 mm) |
| Chassis | 3D-printed, custom mounting parts designed in SolidWorks |

## Package contents

| File | Role |
| --- | --- |
| `launch/lidar.launch.py` | X2 driver + static TF `base_link -> laser_frame` |
| `launch/slam.launch.py` | `slam_toolbox` online_async, optional fake odometry TF |
| `launch/robot_base.launch.py` | Starts `serial_bridge` (serial port as parameter) |
| `launch/full_bringup.launch.py` | URDF + LiDAR + SLAM, each toggled by arguments |
| `scripts/serial_bridge.py` | ROS2 / Arduino bridge: `/cmd_vel` to serial, serial to `/odom` + TF |
| `config/ydlidar_x2.yaml` | LiDAR driver parameters |
| `config/slam_params.yaml` | `slam_toolbox` tuned for weak or absent odometry |
| `config/nav2_params.yaml` | Holonomic Nav2 base (MPPI) for later use |
| `urdf/slam_robot.urdf.xacro` | `base_footprint`, `base_link`, 4 wheels, `laser_frame`, `imu_link` |

Dimensions marked `TODO` in the URDF and in `nav2_params.yaml` (LiDAR height, robot radius, wheelbase) are placeholders to replace with real measurements.

## Build

```
cd ~/ros2_ws
colcon build --packages-select slam_robot_bringup ydlidar_ros2_driver
source install/setup.bash
```

The YDLIDAR driver needs the YDLidar-SDK installed first (see the `ydlidar_ros2_driver` README).

## Quick start

The steps below assume the LiDAR shows up as `/dev/ttyUSB0` (check with `ls /dev/ttyUSB*`) and that the user is in the `dialout` group (`sudo usermod -aG dialout $USER`, then log out and back in).

**1. LiDAR only.** Check the scans in RViz (fixed frame `laser_frame`, add `LaserScan` on `/scan`):

```
ros2 launch slam_robot_bringup lidar.launch.py
```

**2. SLAM with the robot pushed by hand.** No Arduino connected: the launch publishes an identity `odom -> base_footprint` transform and scan matching estimates all motion. Push the robot slowly.

```
ros2 launch slam_robot_bringup slam.launch.py
```

In RViz, set the fixed frame to `map` and add `Map` (`/map`), `LaserScan` and `TF`.

**3. Full bringup.** URDF + LiDAR + SLAM, each toggleable:

```
ros2 launch slam_robot_bringup full_bringup.launch.py
ros2 launch slam_robot_bringup full_bringup.launch.py use_slam:=false
```

**4. Real robot with the Arduino.** Start the serial bridge, then SLAM with the fake odometry disabled so the transform is not published twice:

```
ros2 launch slam_robot_bringup robot_base.launch.py
ros2 launch slam_robot_bringup slam.launch.py publish_fake_odom:=false
```

**5. Save the map** once it looks good:

```
mkdir -p ~/maps
ros2 run nav2_map_server map_saver_cli -f ~/maps/my_map
```

**Important:** whenever `serial_bridge` is running, it publishes `odom -> base_footprint`. Always launch SLAM with `publish_fake_odom:=false` in that case, otherwise two sources publish the same transform and the map breaks.

## Current status

- Motor control (PID + feedforward) on the Arduino: working
- LiDAR acquisition and TF tree (`map -> odom -> base -> laser`): working
- SLAM mapping with `slam_toolbox`: working (real odometry from the Arduino, even approximate, is needed for scan matching to progress)
- Remote teleoperation over WiFi (SSH + ROS2 `/cmd_vel`): working
- Nav2 autonomous navigation: integrated as configuration, MPPI tuning still in progress

## Known issues

- **Nav2 / MPPI tuning is not finished.** Velocity limits and critic weights in `nav2_params.yaml` are a reasonable base, not validated on the real robot.
- **Mechanical rigidity.** The 3D-printed chassis lets vibrations reach the LiDAR while driving. Threaded inserts and stiffer structural parts are needed.
- **Lateral (strafe) motion is limited** by the Mecanum rollers rubbing on the current chassis.
- **Lab WiFi** is occasionally unstable during remote sessions.
- **URDF and Nav2 dimensions** marked `TODO` still need real measurements.

## Author

Ruben Fabioux, internship project at UTP under the supervision of Prof. Rosdiazli.
