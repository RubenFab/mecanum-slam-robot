# Lancement du driver YDLIDAR X2 + TF statique base_link -> laser_frame.
# Cible : ROS2 Humble.
#
# Usage :
#   ros2 launch slam_robot_bringup lidar.launch.py
#   ros2 launch slam_robot_bringup lidar.launch.py port:=/dev/ttyUSB1
#   ros2 launch slam_robot_bringup lidar.launch.py use_static_tf:=false
#
# use_static_tf:=false quand robot_state_publisher publie déjà la TF via
# l'URDF (sinon deux publications concurrentes de la même transformée).

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
            description='Port série du LiDAR (vérifier avec ls /dev/ttyUSB*)'),
        DeclareLaunchArgument(
            'use_static_tf',
            default_value='true',
            description='Publier la TF statique base_link->laser_frame '
                        '(mettre false si robot_state_publisher est actif)'),
        DeclareLaunchArgument(
            'lidar_height',
            default_value='0.20',   # TODO: À MESURER — hauteur du plan laser (m)
            description='Hauteur du LiDAR au-dessus de base_link (m)'),

        # --- Driver YDLIDAR ---
        # Les paramètres viennent de config/ydlidar_x2.yaml ; le port passé en
        # argument de launch écrase celui du yaml (le dict a priorité).
        Node(
            package='ydlidar_ros2_driver',
            executable='ydlidar_ros2_driver_node',
            name='ydlidar_ros2_driver_node',
            output='screen',
            parameters=[lidar_params, {'port': port}],
        ),

        # --- TF statique provisoire base_link -> laser_frame ---
        # À remplacer par l'URDF mesuré (robot_state_publisher) dès que possible.
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
