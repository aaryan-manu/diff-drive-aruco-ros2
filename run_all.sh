#!/bin/bash
# ──────────────────────────────────────────────────────────────────
# run_all.sh — Foolproof 1-Click Launch for DiffBot SLAM
# ──────────────────────────────────────────────────────────────────

echo "[1/4] Cleaning up stale processes and memory..."
killall -9 gzserver gzclient rviz2 robot_state_publisher teleop_twist_keyboard sync_slam_toolbox_node python3 ros2 >/dev/null 2>&1 || true
rm -f /dev/shm/fastrtps_*
ros2 daemon stop >/dev/null 2>&1 || true

# ── FORCED ENVIRONMENT (Bypasses ~/.bashrc entirely) ──
export ROS_LOCALHOST_ONLY=0
export ROS_DOMAIN_ID=189
unset ROS_DISCOVERY_SERVER
unset FASTRTPS_DEFAULT_PROFILES_FILE

source /opt/ros/humble/setup.bash
source install/setup.bash

echo "[2/4] Launching Simulation (Gazebo + RViz)..."
ros2 launch diffbot_slam simulation.launch.py > /tmp/sim_debug.log 2>&1 &
SIM_PID=$!

echo "      Waiting for Gazebo to initialize..."
sleep 10

echo "[3/4] Launching SLAM Toolbox..."
ros2 launch diffbot_slam slam.launch.py > /tmp/slam_debug.log 2>&1 &
SLAM_PID=$!

echo "      Waiting for SLAM to initialize..."
sleep 4

echo "════════════════════════════════════════════════════════════"
echo "  [4/4] All systems GO! Isolated on Domain ID 189."
echo "  Use your keyboard to drive the robot!"
echo "════════════════════════════════════════════════════════════"

# Teleop runs in the foreground so you can interact with it
ros2 run teleop_twist_keyboard teleop_twist_keyboard

# When the user exits Teleop (Ctrl+C or 'q'), clean up everything
echo ""
echo "Cleaning up background processes..."
kill $SLAM_PID $SIM_PID >/dev/null 2>&1 || true
killall -9 gzserver gzclient rviz2 robot_state_publisher sync_slam_toolbox_node >/dev/null 2>&1 || true
echo "Done."
