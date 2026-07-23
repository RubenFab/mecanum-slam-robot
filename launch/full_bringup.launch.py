# Full bringup: robot_state_publisher (URDF) + LiDAR + SLAM.
# Target: ROS2 Humble.
#
# Usage:
#   ros2 launch slam_robot_bringup full_bringup.launch.py
#   ros2 launch slam_robot_bringup full_bringup.launch.py use_slam:=false
#   ros2 launch slam_robot_bringup full_bringup.launch.py use_rsp:=false
#
# Arguments:
#   use_rsp   (true)  : robot_state_publisher with the xacro URDF
#   use_lidar (true)  : YDLIDAR X2 driver
#   use_slam  (true)  : slam_toolbox online async
#   publish_fake_odom (true) : identity TF odom->base_footprint
#                              (false when the Arduino publishes odometry)
#
# When use_rsp:=true, the static TF base_link->laser_frame from the LiDAR launch
# is automatically disabled: the URDF provides the transform.

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration, NotSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    pkg_share = get_package_share_directory('slam_robot_bringup')
    xacro_file = os.path.join(pkg_share, 'urdf', 'slam_robot.urdf.xacro')

    use_rsp = LaunchConfiguration('use_rsp')
    use_lidar = LaunchConfiguration('use_lidar')
    use_slam = LaunchConfiguration('use_slam')
    use_sim_time = LaunchConfiguration('use_sim_time')
    publish_fake_odom = LaunchConfiguration('publish_fake_odom')

    # Generate the robot description from the xacro.
    # ParameterValue(..., value_type=str) is required on Humble so that the
    # output of the xacro command is treated as a string.
    robot_description = ParameterValue(
        Command(['xacro ', xacro_file]),
        value_type=str)

    return LaunchDescription([
        DeclareLaunchArgument('use_rsp', default_value='true',
                              description='Start robot_state_publisher (URDF)'),
        DeclareLaunchArgument('use_lidar', default_value='true',
                              description='Start the YDLIDAR X2 driver'),
        DeclareLaunchArgument('use_slam', default_value='true',
                              description='Start slam_toolbox'),
        DeclareLaunchArgument('use_sim_time', default_value='false',
                              description='Use the simulated clock'),
        DeclareLaunchArgument('publish_fake_odom', default_value='true',
                              description='Identity TF odom->base_footprint '
                                          '(false when the Arduino is connected)'),

        # --- robot_state_publisher: publishes the URDF TFs ---
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            output='screen',
            condition=IfCondition(use_rsp),
            parameters=[{
                'robot_description': robot_description,
                'use_sim_time': use_sim_time,
            }],
        ),

        # --- LiDAR ---
        # use_static_tf = NOT use_rsp: the provisional TF base_link->laser_frame
        # is published only if the URDF is not.
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(pkg_share, 'launch', 'lidar.launch.py')),
            condition=IfCondition(use_lidar),
            launch_arguments={
                'use_static_tf': NotSubstitution(use_rsp),
            }.items(),
        ),

        # --- SLAM ---
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(pkg_share, 'launch', 'slam.launch.py')),
            condition=IfCondition(use_slam),
            launch_arguments={
                'use_sim_time': use_sim_time,
                'publish_fake_odom': publish_fake_odom,
            }.items(),
        ),
    ])
