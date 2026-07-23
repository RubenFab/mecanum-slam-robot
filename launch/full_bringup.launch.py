# Bringup complet : robot_state_publisher (URDF) + LiDAR + SLAM.
# Cible : ROS2 Humble.
#
# Usage :
#   ros2 launch slam_robot_bringup full_bringup.launch.py
#   ros2 launch slam_robot_bringup full_bringup.launch.py use_slam:=false
#   ros2 launch slam_robot_bringup full_bringup.launch.py use_rsp:=false
#
# Arguments :
#   use_rsp   (true)  : robot_state_publisher avec l'URDF xacro
#   use_lidar (true)  : driver YDLIDAR X2
#   use_slam  (true)  : slam_toolbox online async
#   publish_fake_odom (true) : TF identité odom->base_footprint
#                              (false quand l'Arduino publie l'odométrie)
#
# Quand use_rsp:=true, la TF statique base_link->laser_frame du launch LiDAR
# est automatiquement désactivée : c'est l'URDF qui fournit la transformée.

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

    # Génération de la description du robot à partir du xacro.
    # ParameterValue(..., value_type=str) est nécessaire sur Humble pour que
    # le résultat de la commande xacro soit bien traité comme une chaîne.
    robot_description = ParameterValue(
        Command(['xacro ', xacro_file]),
        value_type=str)

    return LaunchDescription([
        DeclareLaunchArgument('use_rsp', default_value='true',
                              description='Lancer robot_state_publisher (URDF)'),
        DeclareLaunchArgument('use_lidar', default_value='true',
                              description='Lancer le driver YDLIDAR X2'),
        DeclareLaunchArgument('use_slam', default_value='true',
                              description='Lancer slam_toolbox'),
        DeclareLaunchArgument('use_sim_time', default_value='false',
                              description='Utiliser l\'horloge simulée'),
        DeclareLaunchArgument('publish_fake_odom', default_value='true',
                              description='TF identité odom->base_footprint '
                                          '(false quand l\'Arduino est branché)'),

        # --- robot_state_publisher : publie les TF de l'URDF ---
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
        # use_static_tf = NOT use_rsp : la TF provisoire base_link->laser_frame
        # n'est publiée que si l'URDF ne l'est pas.
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
