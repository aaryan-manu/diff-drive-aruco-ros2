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
ArUco Semantic Patrol Node.

Maps ArUco marker IDs to Nav2 Goals (NavigateToPose) to create a visual patrol loop:
- See ID 1 (North Wall) -> Go to East Wall
- See ID 2 (East Wall)  -> Go to South Wall
- See ID 3 (South Wall) -> Go to West Wall
- See ID 4 (West Wall)  -> Go to North Wall
"""

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import Int32MultiArray
from sensor_msgs.msg import Image
from nav2_msgs.action import NavigateToPose
from cv_bridge import CvBridge
import cv2
from typing import List


class ArucoCommandFollower(Node):
    """ROS 2 node that maps detected ArUco marker IDs to Nav2 Waypoints."""

    def __init__(self):
        super().__init__('aruco_command_follower')

        # Setup CvBridge
        self.bridge = CvBridge()

        # State tracking
        self.current_target_id = None
        self.is_navigating = False
        self.detected_ids: List[int] = []

        # Waypoint Dictionary: ID -> (x, y, qz, qw, description)
        self.waypoints = {
            1: (3.5, 0.0, 0.0, 1.0, "East Wall"),     # Face East
            2: (0.0, -3.5, -0.707, 0.707, "South Wall"), # Face South
            3: (-3.5, 0.0, 1.0, 0.0, "West Wall"),    # Face West
            4: (0.0, 3.5, 0.707, 0.707, "North Wall") # Face North
        }

        # Nav2 Action Client
        self.nav_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')

        # Subscribers
        self.create_subscription(
            Int32MultiArray, '/aruco/ids', self._ids_callback, 10)
        self.create_subscription(
            Image, '/aruco/image_debug', self._image_callback, 10)

        # Timer loop for state machine
        self.timer = self.create_timer(0.5, self._control_loop)

        self.get_logger().info('ArUco Semantic Patrol node started.')
        self.get_logger().info('Waiting for Nav2 action server...')
        self.nav_client.wait_for_server()
        self.get_logger().info('Nav2 action server connected! Ready for markers.')

    def _ids_callback(self, msg: Int32MultiArray):
        """Store the latest detected marker IDs."""
        self.detected_ids = list(msg.data)

    def _image_callback(self, msg: Image):
        """Display annotated camera feed with active command overlay."""
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')

        # Add text overlay showing active command
        if self.current_target_id:
            cmd_text = f"Navigating to {self.waypoints[self.current_target_id][4]}"
            color = (0, 255, 0)
        else:
            cmd_text = "Awaiting Visual Target..."
            color = (0, 0, 255)

        cv2.putText(frame, cmd_text, (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        cv2.imshow('aruco_semantic_patrol', frame)
        cv2.waitKey(1)

    def send_nav_goal(self, marker_id: int):
        """Send a goal to Nav2 based on the detected marker ID."""
        if marker_id not in self.waypoints:
            return
            
        if self.is_navigating:
            return

        self.get_logger().info(f'Detected Marker {marker_id}! Sending Nav2 goal to {self.waypoints[marker_id][4]}...')
        
        goal_msg = NavigateToPose.Goal()
        goal_msg.pose.header.frame_id = 'map'
        goal_msg.pose.header.stamp = self.get_clock().now().to_msg()
        
        x, y, qz, qw, _ = self.waypoints[marker_id]
        goal_msg.pose.pose.position.x = x
        goal_msg.pose.pose.position.y = y
        goal_msg.pose.pose.orientation.z = qz
        goal_msg.pose.pose.orientation.w = qw

        self.is_navigating = True
        self.current_target_id = marker_id
        
        self._send_goal_future = self.nav_client.send_goal_async(goal_msg)
        self._send_goal_future.add_done_callback(self.goal_response_callback)

    def goal_response_callback(self, future):
        """Handle the response from the Action Server."""
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().info('Goal rejected by Nav2 server.')
            self.is_navigating = False
            self.current_target_id = None
            return
            
        self.get_logger().info('Goal accepted! Robot is driving...')
        self._get_result_future = goal_handle.get_result_async()
        self._get_result_future.add_done_callback(self.get_result_callback)

    def get_result_callback(self, future):
        """Handle completion of the goal."""
        self.get_logger().info('Arrived at destination! Scanning for next marker...')
        self.is_navigating = False
        self.current_target_id = None

    def _control_loop(self):
        """Check for markers and dispatch goals if not already navigating."""
        if not self.detected_ids:
            return

        # Prioritize the lowest ID if multiple are seen
        detected_id = min(self.detected_ids)

        # Only send a new goal if we aren't currently driving
        if not self.is_navigating:
            self.send_nav_goal(detected_id)


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
