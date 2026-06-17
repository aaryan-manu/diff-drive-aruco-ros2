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
ArUco Marker Detector Node.

Detects ArUco markers from the robot's camera and publishes:
  - /aruco/detections  (PoseArray with marker poses)
  - /aruco/ids         (Int32MultiArray with marker IDs)
  - /aruco/image_debug (annotated image for visualisation)
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy

import cv2
import numpy as np
from cv_bridge import CvBridge

from sensor_msgs.msg import Image, CameraInfo
from geometry_msgs.msg import PoseArray, Pose, TransformStamped
from std_msgs.msg import Int32MultiArray
from tf2_ros import TransformBroadcaster


class ArucoDetector(Node):
    """ROS 2 node that detects ArUco markers and publishes their poses."""

    def __init__(self):
        super().__init__('aruco_detector')

        # ── Parameters ──────────────────────────────────────────
        self.declare_parameter('marker_size', 0.2)       # metres
        self.declare_parameter('aruco_dict', 'DICT_4X4_50')
        self.declare_parameter('camera_topic', '/camera/image_raw')
        self.declare_parameter('camera_info_topic', '/camera/camera_info')

        self.marker_size = self.get_parameter('marker_size').value
        dict_name       = self.get_parameter('aruco_dict').value
        cam_topic       = self.get_parameter('camera_topic').value
        cam_info_topic  = self.get_parameter('camera_info_topic').value

        # ── ArUco Setup ──────────────────────────────────────────
        aruco_dicts = {
            'DICT_4X4_50':  cv2.aruco.DICT_4X4_50,
            'DICT_4X4_100': cv2.aruco.DICT_4X4_100,
            'DICT_5X5_100': cv2.aruco.DICT_5X5_100,
            'DICT_6X6_250': cv2.aruco.DICT_6X6_250,
        }
        self.aruco_dict   = cv2.aruco.getPredefinedDictionary(aruco_dicts[dict_name])
        self.aruco_params = cv2.aruco.DetectorParameters()
        self.detector     = cv2.aruco.ArucoDetector(self.aruco_dict, self.aruco_params)

        self.bridge       = CvBridge()
        self.camera_matrix = None
        self.dist_coeffs   = None
        self.tf_broadcaster = TransformBroadcaster(self)

        # Pre-compute 3-D object points for solvePnP (marker in its own frame)
        half = self.marker_size / 2.0
        self.marker_obj_points = np.array([
            [-half,  half, 0.0],
            [ half,  half, 0.0],
            [ half, -half, 0.0],
            [-half, -half, 0.0],
        ], dtype=np.float32)

        # ── QoS ─────────────────────────────────────────────────
        sensor_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
        )

        # ── Subscriptions ────────────────────────────────────────
        self.create_subscription(CameraInfo, cam_info_topic,
                                 self._camera_info_cb, 10)
        self.create_subscription(Image, cam_topic,
                                 self._image_cb, sensor_qos)

        # ── Publishers ───────────────────────────────────────────
        self.pose_pub  = self.create_publisher(PoseArray, '/aruco/detections', 10)
        self.id_pub    = self.create_publisher(Int32MultiArray, '/aruco/ids', 10)
        self.debug_pub = self.create_publisher(Image, '/aruco/image_debug', 10)

        self.get_logger().info('ArUco Detector node started.')

    # ────────────────────────────────────────────────────────────
    def _camera_info_cb(self, msg: CameraInfo):
        if self.camera_matrix is None:
            self.camera_matrix = np.array(msg.k).reshape(3, 3)
            self.dist_coeffs   = np.array(msg.d)
            self.get_logger().info('Camera intrinsics received.')

    # ────────────────────────────────────────────────────────────
    def _estimate_pose_single_markers(self, corners):
        """Estimate pose of each detected marker using cv2.solvePnP.

        This replaces the deprecated cv2.aruco.estimatePoseSingleMarkers
        which was removed in OpenCV 4.7+.

        Returns:
            rvecs: list of rotation vectors (one per marker)
            tvecs: list of translation vectors (one per marker)
        """
        rvecs = []
        tvecs = []
        for corner in corners:
            image_points = corner.reshape((4, 2))
            success, rvec, tvec = cv2.solvePnP(
                self.marker_obj_points,
                image_points,
                self.camera_matrix,
                self.dist_coeffs,
                flags=cv2.SOLVEPNP_IPPE_SQUARE,
            )
            if success:
                rvecs.append(rvec.flatten())
                tvecs.append(tvec.flatten())
        return rvecs, tvecs

    # ────────────────────────────────────────────────────────────
    def _image_cb(self, msg: Image):
        if self.camera_matrix is None:
            return

        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        corners, ids, _ = self.detector.detectMarkers(gray)

        pose_array = PoseArray()
        pose_array.header.stamp    = msg.header.stamp
        pose_array.header.frame_id = 'camera_optical_link'

        id_msg = Int32MultiArray()

        if ids is not None:
            cv2.aruco.drawDetectedMarkers(frame, corners, ids)

            rvecs, tvecs = self._estimate_pose_single_markers(corners)

            for i, marker_id in enumerate(ids.flatten()):
                if i >= len(rvecs):
                    break  # solvePnP may fail for some markers

                rvec = rvecs[i]
                tvec = tvecs[i]

                # Draw axis
                cv2.drawFrameAxes(frame, self.camera_matrix,
                                  self.dist_coeffs, rvec, tvec,
                                  self.marker_size * 0.5)

                # Build Pose msg
                pose = Pose()
                pose.position.x = float(tvec[0])
                pose.position.y = float(tvec[1])
                pose.position.z = float(tvec[2])

                # Rodrigues -> quaternion
                rot_mat, _ = cv2.Rodrigues(rvec)
                q = self._rotation_matrix_to_quaternion(rot_mat)
                pose.orientation.x = q[0]
                pose.orientation.y = q[1]
                pose.orientation.z = q[2]
                pose.orientation.w = q[3]

                pose_array.poses.append(pose)
                id_msg.data.append(int(marker_id))

                # Broadcast TF: camera -> aruco_<id>
                self._broadcast_marker_tf(msg.header.stamp,
                                          marker_id, tvec, rvec)

                self.get_logger().debug(
                    f'Marker {marker_id}: pos=({tvec[0]:.2f}, '
                    f'{tvec[1]:.2f}, {tvec[2]:.2f})'
                )

        self.pose_pub.publish(pose_array)
        self.id_pub.publish(id_msg)

        debug_msg = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
        debug_msg.header = msg.header
        self.debug_pub.publish(debug_msg)

    # ────────────────────────────────────────────────────────────
    def _broadcast_marker_tf(self, stamp, marker_id, tvec, rvec):
        tf = TransformStamped()
        tf.header.stamp    = stamp
        tf.header.frame_id = 'camera_optical_link'
        tf.child_frame_id  = f'aruco_{marker_id}'

        tf.transform.translation.x = float(tvec[0])
        tf.transform.translation.y = float(tvec[1])
        tf.transform.translation.z = float(tvec[2])

        rot_mat, _ = cv2.Rodrigues(rvec)
        q = self._rotation_matrix_to_quaternion(rot_mat)
        tf.transform.rotation.x = q[0]
        tf.transform.rotation.y = q[1]
        tf.transform.rotation.z = q[2]
        tf.transform.rotation.w = q[3]

        self.tf_broadcaster.sendTransform(tf)

    # ────────────────────────────────────────────────────────────
    @staticmethod
    def _rotation_matrix_to_quaternion(R):
        """Convert 3x3 rotation matrix to quaternion (x,y,z,w)."""
        trace = R[0, 0] + R[1, 1] + R[2, 2]
        if trace > 0:
            s = 0.5 / np.sqrt(trace + 1.0)
            w = 0.25 / s
            x = (R[2, 1] - R[1, 2]) * s
            y = (R[0, 2] - R[2, 0]) * s
            z = (R[1, 0] - R[0, 1]) * s
        elif R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
            s = 2.0 * np.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2])
            w = (R[2, 1] - R[1, 2]) / s
            x = 0.25 * s
            y = (R[0, 1] + R[1, 0]) / s
            z = (R[0, 2] + R[2, 0]) / s
        elif R[1, 1] > R[2, 2]:
            s = 2.0 * np.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2])
            w = (R[0, 2] - R[2, 0]) / s
            x = (R[0, 1] + R[1, 0]) / s
            y = 0.25 * s
            z = (R[1, 2] + R[2, 1]) / s
        else:
            s = 2.0 * np.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1])
            w = (R[1, 0] - R[0, 1]) / s
            x = (R[0, 2] + R[2, 0]) / s
            y = (R[1, 2] + R[2, 1]) / s
            z = 0.25 * s
        return [x, y, z, w]


def main(args=None):
    rclpy.init(args=args)
    node = ArucoDetector()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
