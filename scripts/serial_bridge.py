#!/usr/bin/env python3
# ============================================================================
#  serial_bridge.py -- ROS2 <-> Arduino Mega serial bridge (Mecanum SLAM robot)
# ============================================================================
#
#  Role: link the ROS2 graph (on the CAPA55R) to the Arduino Mega firmware,
#  which communicates over the USB serial link in plain text.
#
#     /cmd_vel  (geometry_msgs/Twist)  ->  serial  "V,vx,vy,wz\n"
#     serial  "O,x,y,th,vx,vy,wz\n"    ->  /odom  (nav_msgs/Odometry)
#                                      ->  TF  odom -> base_footprint
#
#  Conventions IMPOSED by the slam_toolbox config (slam_params.yaml):
#     - odometry topic : /odom
#     - odom_frame  : odom
#     - base_frame  : base_footprint
#     - command topic : /cmd_vel
#
#  WARNING: TF CONFLICT TO AVOID
#  This node publishes the TF  odom -> base_footprint.
#  slam.launch.py ALSO publishes this TF (identity) when
#  publish_fake_odom:=true (its default).
#  => When you start THIS bridge, ALWAYS start SLAM with:
#         ros2 launch slam_robot_bringup slam.launch.py publish_fake_odom:=false
#  otherwise two sources publish the same TF and the map breaks.
#
#  Launch:
#     ros2 run slam_robot_bringup serial_bridge          (default port)
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
    """Convert a yaw angle (rad) into a quaternion (planar rotation about Z)."""
    q = Quaternion()
    q.z = math.sin(yaw / 2.0)
    q.w = math.cos(yaw / 2.0)
    return q


class SerialBridge(Node):
    def __init__(self):
        super().__init__('serial_bridge')

        # ------------------ Parameters ------------------
        self.declare_parameter('port', '/dev/ttyACM0')
        self.declare_parameter('baudrate', 115200)
        self.declare_parameter('odom_frame', 'odom')
        self.declare_parameter('base_frame', 'base_footprint')
        self.declare_parameter('publish_tf', True)  # set False if another node publishes the TF

        port = self.get_parameter('port').value
        baud = self.get_parameter('baudrate').value
        self.odom_frame = self.get_parameter('odom_frame').value
        self.base_frame = self.get_parameter('base_frame').value
        self.publish_tf = self.get_parameter('publish_tf').value

        # ------------------ Serial link ------------------
        try:
            self.ser = serial.Serial(port, baud, timeout=0.1)
            self.get_logger().info(f'Serial port opened: {port} @ {baud} baud')
        except serial.SerialException as e:
            self.get_logger().error(f'Cannot open {port}: {e}')
            raise

        # ------------------ Publishers / Subscribers ------------------
        qos = QoSProfile(depth=10)
        self.odom_pub = self.create_publisher(Odometry, 'odom', qos)
        self.cmd_sub = self.create_subscription(Twist, 'cmd_vel', self.cmd_cb, qos)
        self.tf_broadcaster = TransformBroadcaster(self)

        # ------------------ Serial read in a separate thread ------------------
        self._buf = b''
        self._running = True
        self._reader = threading.Thread(target=self.read_loop, daemon=True)
        self._reader.start()

        self.get_logger().info('serial_bridge ready. Waiting for /cmd_vel and "O,..." frames.')
        if self.publish_tf:
            self.get_logger().warn(
                'publish_tf=True: this node publishes odom->base_footprint. '
                'Start SLAM with publish_fake_odom:=false to avoid a TF conflict.')

    # ---------- /cmd_vel -> serial ----------
    def cmd_cb(self, msg: Twist):
        vx = msg.linear.x
        vy = msg.linear.y      # non-zero only in holonomic mode (Mecanum)
        wz = msg.angular.z
        line = f'V,{vx:.4f},{vy:.4f},{wz:.4f}\n'
        try:
            self.ser.write(line.encode('ascii'))
        except serial.SerialException as e:
            self.get_logger().error(f'Serial write failed: {e}')

    # ---------- serial -> /odom + TF ----------
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
            return  # ignore the "E,..." debug frames and noise
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
