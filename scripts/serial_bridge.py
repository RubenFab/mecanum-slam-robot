#!/usr/bin/env python3
# ============================================================================
#  serial_bridge.py — Pont série ROS2 <-> Arduino Mega (robot SLAM Mecanum)
# ============================================================================
#
#  Rôle : faire le lien entre le graphe ROS2 (sur le CAPA55R) et le firmware
#  de l'Arduino Mega, qui communique par liaison série USB en texte simple.
#
#     /cmd_vel  (geometry_msgs/Twist)  ->  série  "V,vx,vy,wz\n"
#     série  "O,x,y,th,vx,vy,wz\n"     ->  /odom  (nav_msgs/Odometry)
#                                      ->  TF  odom -> base_footprint
#
#  Conventions IMPOSÉES par la config slam_toolbox (slam_params.yaml) :
#     - topic odométrie : /odom
#     - odom_frame  : odom
#     - base_frame  : base_footprint
#     - topic consigne : /cmd_vel
#
#  ⚠️  CONFLIT DE TF À ÉVITER
#  Ce nœud publie la TF  odom -> base_footprint.
#  La slam.launch.py publie AUSSI cette TF (identité) quand
#  publish_fake_odom:=true (son défaut).
#  => Quand tu lances CE pont, lance TOUJOURS le SLAM avec :
#         ros2 launch slam_robot_bringup slam.launch.py publish_fake_odom:=false
#  sinon deux sources publient la même TF et la carte part en vrille.
#
#  Lancement :
#     ros2 run slam_robot_bringup serial_bridge          (port par défaut)
#     ros2 run slam_robot_bringup serial_bridge --ros-args -p port:=/dev/ttyACM0
# ============================================================================

import math
import threading

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile

import serial

from geometry_msgs.msg import Twist, TransformStamped, Quaternion
from nav_msgs.msg import Odometry
from tf2_ros import TransformBroadcaster


def yaw_to_quaternion(yaw: float) -> Quaternion:
    """Convertit un angle de lacet (rad) en quaternion (rotation plane autour de Z)."""
    q = Quaternion()
    q.z = math.sin(yaw / 2.0)
    q.w = math.cos(yaw / 2.0)
    return q


class SerialBridge(Node):
    def __init__(self):
        super().__init__('serial_bridge')

        # ------------------ Paramètres ------------------
        self.declare_parameter('port', '/dev/ttyACM0')
        self.declare_parameter('baudrate', 115200)
        self.declare_parameter('odom_frame', 'odom')
        self.declare_parameter('base_frame', 'base_footprint')
        self.declare_parameter('publish_tf', True)  # mettre False si un autre nœud publie la TF

        port = self.get_parameter('port').value
        baud = self.get_parameter('baudrate').value
        self.odom_frame = self.get_parameter('odom_frame').value
        self.base_frame = self.get_parameter('base_frame').value
        self.publish_tf = self.get_parameter('publish_tf').value

        # ------------------ Liaison série ------------------
        try:
            self.ser = serial.Serial(port, baud, timeout=0.1)
            self.get_logger().info(f'Port série ouvert : {port} @ {baud} bauds')
        except serial.SerialException as e:
            self.get_logger().error(f'Impossible d\'ouvrir {port} : {e}')
            raise

        # ------------------ Publishers / Subscribers ------------------
        qos = QoSProfile(depth=10)
        self.odom_pub = self.create_publisher(Odometry, 'odom', qos)
        self.cmd_sub = self.create_subscription(Twist, 'cmd_vel', self.cmd_cb, qos)
        self.tf_broadcaster = TransformBroadcaster(self)

        # ------------------ Lecture série en thread séparé ------------------
        self._buf = b''
        self._running = True
        self._reader = threading.Thread(target=self.read_loop, daemon=True)
        self._reader.start()

        self.get_logger().info('serial_bridge prêt. En attente de /cmd_vel et de trames "O,...".')
        if self.publish_tf:
            self.get_logger().warn(
                'publish_tf=True : ce nœud publie odom->base_footprint. '
                'Lance le SLAM avec publish_fake_odom:=false pour éviter un conflit de TF.')

    # ---------- /cmd_vel -> série ----------
    def cmd_cb(self, msg: Twist):
        vx = msg.linear.x
        vy = msg.linear.y      # non nul seulement en holonome (Mecanum)
        wz = msg.angular.z
        line = f'V,{vx:.4f},{vy:.4f},{wz:.4f}\n'
        try:
            self.ser.write(line.encode('ascii'))
        except serial.SerialException as e:
            self.get_logger().error(f'Écriture série échouée : {e}')

    # ---------- série -> /odom + TF ----------
    def read_loop(self):
        while self._running:
            try:
                data = self.ser.read(128)
            except serial.SerialException:
                continue
            if not data:
                continue
            self._buf += data
            while b'\n' in self._buf:
                raw, self._buf = self._buf.split(b'\n', 1)
                self.handle_line(raw.decode('ascii', errors='ignore').strip())

    def handle_line(self, line: str):
        if not line or line[0] != 'O':
            return  # on ignore les trames debug "E,..." et le bruit
        parts = line.split(',')
        if len(parts) != 7:
            return
        try:
            x, y, th, vx, vy, vth = (float(p) for p in parts[1:])
        except ValueError:
            return
        self.publish_odom(x, y, th, vx, vy, vth)

    def publish_odom(self, x, y, th, vx, vy, vth):
        now = self.get_clock().now().to_msg()

        odom = Odometry()
        odom.header.stamp = now
        odom.header.frame_id = self.odom_frame
        odom.child_frame_id = self.base_frame
        odom.pose.pose.position.x = x
        odom.pose.pose.position.y = y
        odom.pose.pose.orientation = yaw_to_quaternion(th)
        odom.twist.twist.linear.x = vx
        odom.twist.twist.linear.y = vy
        odom.twist.twist.angular.z = vth
        self.odom_pub.publish(odom)

        if self.publish_tf:
            t = TransformStamped()
            t.header.stamp = now
            t.header.frame_id = self.odom_frame
            t.child_frame_id = self.base_frame
            t.transform.translation.x = x
            t.transform.translation.y = y
            t.transform.rotation = yaw_to_quaternion(th)
            self.tf_broadcaster.sendTransform(t)

    def destroy_node(self):
        self._running = False
        try:
            self.ser.close()
        except Exception:
            pass
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = SerialBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
