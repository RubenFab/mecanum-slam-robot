# Launch the ROS2 <-> Arduino Mega serial bridge (serial_bridge node) -- ROS2 Humble.
#
# Usage:
#   ros2 launch slam_robot_bringup robot_base.launch.py
#   ros2 launch slam_robot_bringup robot_base.launch.py port:=/dev/ttyACM1
#
# This launch starts the serial_bridge node, which:
#   - subscribes to /cmd_vel (geometry_msgs/Twist) and sends it to the Arduino,
#   - publishes /odom (nav_msgs/Odometry) from the Arduino's "O,..." frames,
#   - publishes the TF  odom -> base_footprint.
#
# WARNING: TF CONFLICT -- READ THIS
# serial_bridge publishes odom -> base_footprint (publish_tf=true by default).
# slam.launch.py ALSO publishes this TF (identity) when publish_fake_odom:=true
# (its default). So ALWAYS launch SLAM with:
#     ros2 launch slam_robot_bringup slam.launch.py publish_fake_odom:=false
# when this bridge is running, otherwise two sources publish the same TF.

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    port = LaunchConfiguration('port')
    baudrate = LaunchConfiguration('baudrate')
    publish_tf = LaunchConfiguration('publish_tf')

    return LaunchDescription([
        DeclareLaunchArgument(
            'port',
            default_value='/dev/ttyACM0',
            description='Arduino Mega serial port'),
        DeclareLaunchArgument(
            'baudrate',
            default_value='115200',
            description='Serial link baud rate'),
        DeclareLaunchArgument(
            'publish_tf',
            default_value='true',
            description='Publish the odom->base_footprint TF from odometry '
                        '(set false if another source publishes this TF)'),

        Node(
            package='slam_robot_bringup',
            executable='serial_bridge',
            name='serial_bridge',
            output='screen',
            parameters=[{
                'port': port,
                'baudrate': baudrate,
                'publish_tf': publish_tf,
            }],
        ),
    ])
