# Launch slam_toolbox (online async) -- ROS2 Humble.
#
# Usage:
#   ros2 launch slam_robot_bringup slam.launch.py
#   ros2 launch slam_robot_bringup slam.launch.py publish_fake_odom:=false
#
# publish_fake_odom (default true): publishes a static IDENTITY TF
# odom -> base_footprint. This is the "no Arduino" mode: slam_toolbox requires
# a complete odom->base TF chain; with this identity TF, all of the robot's
# motion is absorbed by the map->odom correction computed by scan matching.
# Good enough for tests where the robot is pushed by hand.
#
# IMPORTANT: pass publish_fake_odom:=false as soon as the Arduino (serial
# bridge) publishes the real odom->base_footprint TF, otherwise TF conflict.

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_share = get_package_share_directory('slam_robot_bringup')
    slam_params = os.path.join(pkg_share, 'config', 'slam_params.yaml')

    use_sim_time = LaunchConfiguration('use_sim_time')
    publish_fake_odom = LaunchConfiguration('publish_fake_odom')

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='false',
            description='Use the simulated clock (Gazebo)'),
        DeclareLaunchArgument(
            'publish_fake_odom',
            default_value='true',
            description='Publish an identity TF odom->base_footprint '
                        '(set false when the Arduino publishes real odometry)'),

        # --- Identity TF odom -> base_footprint (no-odometry mode) ---
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='static_tf_fake_odom',
            output='screen',
            condition=IfCondition(publish_fake_odom),
            arguments=[
                '--x', '0', '--y', '0', '--z', '0',
                '--roll', '0', '--pitch', '0', '--yaw', '0',
                '--frame-id', 'odom',
                '--child-frame-id', 'base_footprint',
            ],
        ),

        # --- slam_toolbox in online asynchronous mode ---
        # "async" = process the latest available scan without blocking if the
        # CPU cannot keep up -- recommended on an embedded machine like the CAPA55R.
        Node(
            package='slam_toolbox',
            executable='async_slam_toolbox_node',
            name='slam_toolbox',
            output='screen',
            parameters=[slam_params, {'use_sim_time': use_sim_time}],
        ),
    ])
