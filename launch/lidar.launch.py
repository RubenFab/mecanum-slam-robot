# Launch the YDLIDAR X2 driver + static TF base_link -> laser_frame.
# Target: ROS2 Humble.
#
# Usage:
#   ros2 launch slam_robot_bringup lidar.launch.py
#   ros2 launch slam_robot_bringup lidar.launch.py port:=/dev/ttyUSB1
#   ros2 launch slam_robot_bringup lidar.launch.py use_static_tf:=false
#
# use_static_tf:=false when robot_state_publisher already publishes the TF via
# the URDF (otherwise two concurrent publishers of the same transform).

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_share = get_package_share_directory('slam_robot_bringup')
    lidar_params = os.path.join(pkg_share, 'config', 'ydlidar_x2.yaml')

    port = LaunchConfiguration('port')
    use_static_tf = LaunchConfiguration('use_static_tf')
    lidar_height = LaunchConfiguration('lidar_height')

    return LaunchDescription([
        DeclareLaunchArgument(
            'port',
            default_value='/dev/ttyUSB0',
            description='LiDAR serial port (check with ls /dev/ttyUSB*)'),
        DeclareLaunchArgument(
            'use_static_tf',
            default_value='true',
            description='Publish the static TF base_link->laser_frame '
                        '(set false if robot_state_publisher is active)'),
        DeclareLaunchArgument(
            'lidar_height',
            default_value='0.20',   # TODO: MEASURE -- laser plane height (m)
            description='LiDAR height above base_link (m)'),

        # --- YDLIDAR driver ---
        # Parameters come from config/ydlidar_x2.yaml; the port passed as a
        # launch argument overrides the one in the yaml (the dict takes priority).
        Node(
            package='ydlidar_ros2_driver',
            executable='ydlidar_ros2_driver_node',
            name='ydlidar_ros2_driver_node',
            output='screen',
            parameters=[lidar_params, {'port': port}],
        ),

        # --- Provisional static TF base_link -> laser_frame ---
        # Replace with the measured URDF (robot_state_publisher) as soon as possible.
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='static_tf_base_to_laser',
            output='screen',
            condition=IfCondition(use_static_tf),
            arguments=[
                '--x', '0', '--y', '0', '--z', lidar_height,
                '--roll', '0', '--pitch', '0', '--yaw', '0',
                '--frame-id', 'base_link',
                '--child-frame-id', 'laser_frame',
            ],
        ),
    ])
