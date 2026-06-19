#!/bin/bash
# ──────────────────────────────────────────────────────────────────
# run_nav.sh — 1-Click Launch for DiffBot Auto-Navigation & ArUco
# ──────────────────────────────────────────────────────────────────

echo "[1/6] Cleaning up stale processes and memory..."
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

echo "[2/6] Launching Simulation (Gazebo + RViz)..."
ros2 launch diffbot_slam simulation.launch.py > /tmp/sim_debug.log 2>&1 &
SIM_PID=$!

echo "      Waiting for Gazebo to initialize..."
sleep 10

echo "[3/6] Launching SLAM Toolbox (for Mapping & Localization)..."
ros2 launch diffbot_slam slam.launch.py > /tmp/slam_debug.log 2>&1 &
SLAM_PID=$!

echo "      Waiting for SLAM to initialize..."
sleep 5

echo "[4/6] Launching Nav2 (Auto-Navigation Stack)..."
ros2 launch diffbot_slam navigation.launch.py > /tmp/nav_debug.log 2>&1 &
NAV_PID=$!

echo "      Waiting for Nav2 to initialize..."
sleep 8

echo "[5/6] Launching ArUco Command Follower..."
ros2 run diffbot_slam aruco_command_follower > /tmp/aruco_debug.log 2>&1 &
ARUCO_PID=$!

echo "════════════════════════════════════════════════════════════"
echo "  [6/6] All systems GO! Isolated on Domain ID 189."
echo "  You can now use '2D Goal Pose' in RViz to Auto-Navigate!"
echo "  ArUco markers will automatically move the robot."
echo "════════════════════════════════════════════════════════════"
echo "Press ENTER to safely shut down everything..."
read -r

echo "Cleaning up background processes..."
kill $ARUCO_PID $NAV_PID $SLAM_PID $SIM_PID >/dev/null 2>&1 || true
killall -9 gzserver gzclient rviz2 robot_state_publisher sync_slam_toolbox_node >/dev/null 2>&1 || true
echo "Done."
