# Lancement du pont série ROS2 <-> Arduino Mega (nœud serial_bridge) — ROS2 Humble.
#
# Usage :
#   ros2 launch slam_robot_bringup robot_base.launch.py
#   ros2 launch slam_robot_bringup robot_base.launch.py port:=/dev/ttyACM1
#
# Ce launch démarre le nœud serial_bridge, qui :
#   - souscrit /cmd_vel (geometry_msgs/Twist) et l'envoie à l'Arduino,
#   - publie /odom (nav_msgs/Odometry) à partir des trames "O,..." de l'Arduino,
#   - publie la TF  odom -> base_footprint.
#
# ⚠️  CONFLIT DE TF — À LIRE
# serial_bridge publie odom -> base_footprint (publish_tf=true par défaut).
# slam.launch.py publie AUSSI cette TF (identité) quand publish_fake_odom:=true
# (son défaut). Il faut donc TOUJOURS lancer le SLAM avec :
#     ros2 launch slam_robot_bringup slam.launch.py publish_fake_odom:=false
# quand ce pont tourne, sinon deux sources publient la même TF.

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
            description='Port série de l\'Arduino Mega'),
        DeclareLaunchArgument(
            'baudrate',
            default_value='115200',
            description='Débit de la liaison série (bauds)'),
        DeclareLaunchArgument(
            'publish_tf',
            default_value='true',
            description='Publier la TF odom->base_footprint depuis l\'odométrie '
                        '(mettre false si une autre source publie cette TF)'),

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
