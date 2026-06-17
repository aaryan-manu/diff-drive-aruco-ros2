#!/usr/bin/env python3
# Copyright 2024 Aaryan
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
ArUco Command Follower Node.

Maps ArUco marker IDs to velocity commands:
- ID 1: Turn Left
- ID 2: Turn Right
- ID 3: Move Forward
- ID 4: Move Backward
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Int32MultiArray
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
from typing import List


class ArucoCommandFollower(Node):
    """ROS 2 node that maps detected ArUco marker IDs to velocity commands."""

    def __init__(self):
        super().__init__('aruco_command_follower')

        # Current detected IDs
        self.detected_ids: List[int] = []

        # Setup CvBridge
        self.bridge = CvBridge()

        # Publishers
        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)

        # Subscribers
        self.create_subscription(
            Int32MultiArray, '/aruco/ids', self._ids_callback, 10)
        self.create_subscription(
            Image, '/aruco/image_debug', self._image_callback, 10)

        # Timer loop for sending commands and handling OpenCV window
        self.timer = self.create_timer(0.1, self._control_loop)

        self.get_logger().info('ArUco Command Follower node started.')
        self.get_logger().info('Mappings: 1=Left, 2=Right, 3=Forward, 4=Backward')

    def _ids_callback(self, msg: Int32MultiArray):
        """Store the latest detected marker IDs."""
        self.detected_ids = list(msg.data)

    def _image_callback(self, msg: Image):
        """Display annotated camera feed with active command overlay."""
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')

        # Add text overlay showing active command
        cmd_text = "Command: STOP"
        color = (0, 0, 255)  # Red for stop

        if 1 in self.detected_ids:
            cmd_text = "Command: LEFT"
            color = (0, 255, 0)
        elif 2 in self.detected_ids:
            cmd_text = "Command: RIGHT"
            color = (0, 255, 0)
        elif 3 in self.detected_ids:
            cmd_text = "Command: FORWARD"
            color = (0, 255, 0)
        elif 4 in self.detected_ids:
            cmd_text = "Command: BACKWARD"
            color = (0, 255, 0)

        cv2.putText(frame, cmd_text, (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
        cv2.imshow('aruco_command_follower', frame)
        cv2.waitKey(1)

    def _control_loop(self):
        """Publish velocity commands based on detected ArUco marker IDs."""
        twist = Twist()

        # Command logic based on IDs
        if 3 in self.detected_ids:
            # ID 3: Move Forward
            twist.linear.x = 0.2
        elif 4 in self.detected_ids:
            # ID 4: Move Backward
            twist.linear.x = -0.2
        elif 1 in self.detected_ids:
            # ID 1: Turn Left
            twist.angular.z = 0.5
        elif 2 in self.detected_ids:
            # ID 2: Turn Right
            twist.angular.z = -0.5

        # If no known ID is detected, twist remains all zeros (Stop)
        self.cmd_pub.publish(twist)


def main(args=None):
    rclpy.init(args=args)
    node = ArucoCommandFollower()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        cv2.destroyAllWindows()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
