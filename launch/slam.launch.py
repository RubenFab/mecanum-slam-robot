# Lancement de slam_toolbox (online async) — ROS2 Humble.
#
# Usage :
#   ros2 launch slam_robot_bringup slam.launch.py
#   ros2 launch slam_robot_bringup slam.launch.py publish_fake_odom:=false
#
# publish_fake_odom (défaut true) : publie une TF statique IDENTITÉ
# odom -> base_footprint. C'est le mode "sans Arduino" : slam_toolbox exige
# une chaîne TF odom->base complète ; avec cette TF identité, tout le
# déplacement du robot est absorbé par la correction map->odom calculée par
# le scan matching. Suffisant pour les tests en poussant le robot à la main.
#
# IMPORTANT : passer publish_fake_odom:=false dès que l'Arduino (micro-ROS)
# publie la vraie TF odom->base_footprint, sinon conflit de TF.

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
            description='Utiliser l\'horloge simulée (Gazebo)'),
        DeclareLaunchArgument(
            'publish_fake_odom',
            default_value='true',
            description='Publier une TF identité odom->base_footprint '
                        '(mettre false quand l\'Arduino publie la vraie odométrie)'),

        # --- TF identité odom -> base_footprint (mode sans odométrie) ---
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

        # --- slam_toolbox en mode online asynchrone ---
        # "async" = traite le dernier scan disponible sans bloquer si le CPU
        # ne suit pas — recommandé sur une machine embarquée comme le CAPA55R.
        Node(
            package='slam_toolbox',
            executable='async_slam_toolbox_node',
            name='slam_toolbox',
            output='screen',
            parameters=[slam_params, {'use_sim_time': use_sim_time}],
        ),
    ])
