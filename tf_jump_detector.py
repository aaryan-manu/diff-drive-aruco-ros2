#!/usr/bin/env python3
"""
TF Time Jump Diagnostic Tool.

Subscribes to /tf and /clock, detects backward time jumps per transform,
and reports which parent→child frame pair is responsible.

Usage:
    python3 tf_jump_detector.py

Run this ALONGSIDE the simulation to catch time jumps as they happen.
Press Ctrl+C to stop and see a summary.
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from tf2_msgs.msg import TFMessage
from rosgraph_msgs.msg import Clock


class TFJumpDetector(Node):
    def __init__(self):
        super().__init__('tf_jump_detector')

        # Track the latest timestamp seen for each transform pair
        self.latest_time = {}   # (parent, child) -> last_stamp_float
        self.jump_count = {}    # (parent, child) -> count
        self.clock_time = 0.0
        self.total_jumps = 0

        # Subscribe to /tf (dynamic transforms)
        self.create_subscription(
            TFMessage, '/tf', self._tf_cb,
            QoSProfile(
                reliability=ReliabilityPolicy.BEST_EFFORT,
                history=HistoryPolicy.KEEP_LAST,
                depth=100,
            )
        )

        # Subscribe to /tf_static
        self.create_subscription(
            TFMessage, '/tf_static', self._tf_static_cb,
            QoSProfile(
                reliability=ReliabilityPolicy.RELIABLE,
                history=HistoryPolicy.KEEP_LAST,
                depth=100,
            )
        )

        # Subscribe to /clock
        self.create_subscription(
            Clock, '/clock', self._clock_cb,
            QoSProfile(
                reliability=ReliabilityPolicy.BEST_EFFORT,
                history=HistoryPolicy.KEEP_LAST,
                depth=1,
            )
        )

        self.get_logger().info('TF Jump Detector started. Monitoring /tf and /clock...')

    def _stamp_to_float(self, stamp):
        return stamp.sec + stamp.nanosec * 1e-9

    def _clock_cb(self, msg):
        t = self._stamp_to_float(msg.clock)
        if t < self.clock_time and self.clock_time > 0:
            self.get_logger().error(
                f'*** /clock JUMPED BACKWARDS: {self.clock_time:.3f} → {t:.3f} '
                f'(delta = {t - self.clock_time:.3f}s)'
            )
        self.clock_time = t

    def _tf_cb(self, msg):
        self._check_transforms(msg, static=False)

    def _tf_static_cb(self, msg):
        self._check_transforms(msg, static=True)

    def _check_transforms(self, msg, static):
        topic = '/tf_static' if static else '/tf'
        for tf in msg.transforms:
            parent = tf.header.frame_id
            child = tf.child_frame_id
            t = self._stamp_to_float(tf.header.stamp)
            key = (parent, child)

            prev = self.latest_time.get(key, -1.0)
            if prev > 0 and t < prev:
                delta = t - prev
                self.jump_count[key] = self.jump_count.get(key, 0) + 1
                self.total_jumps += 1

                # Only log first 20 jumps per pair to avoid spam
                if self.jump_count[key] <= 20:
                    self.get_logger().warn(
                        f'JUMP BACK on {topic}: {parent} → {child}  '
                        f't={t:.3f} < prev={prev:.3f}  '
                        f'delta={delta:.4f}s  '
                        f'(clock={self.clock_time:.3f})'
                    )
                elif self.jump_count[key] == 21:
                    self.get_logger().warn(
                        f'... suppressing further logs for {parent} → {child} '
                        f'(already {self.jump_count[key]} jumps)'
                    )

            self.latest_time[key] = max(t, prev) if prev > 0 else t

    def print_summary(self):
        print('\n' + '=' * 60)
        print('TF JUMP SUMMARY')
        print('=' * 60)
        if not self.jump_count:
            print('No backward time jumps detected!')
        else:
            print(f'Total jumps: {self.total_jumps}')
            print(f'{"Parent → Child":<40} {"Jumps":>8}')
            print('-' * 50)
            for (parent, child), count in sorted(
                self.jump_count.items(), key=lambda x: -x[1]
            ):
                print(f'{parent} → {child:<30} {count:>8}')
        print('=' * 60)


def main():
    rclpy.init()
    node = TFJumpDetector()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.print_summary()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
