#!/bin/bash
# ──────────────────────────────────────────────────────────────────
# clean_restart.sh — Clean restart helper for DiffBot SLAM
#
# Kills stale Gazebo/RViz/ROS 2 processes, removes leftover
# FastRTPS shared-memory segments, and restarts the ROS 2 daemon.
#
# Run this BEFORE launching the simulation to ensure a clean slate.
#
# Usage:
#   ./clean_restart.sh            # clean only
#   ./clean_restart.sh --launch   # clean + launch simulation
# ──────────────────────────────────────────────────────────────────
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}╔══════════════════════════════════════════╗${NC}"
echo -e "${YELLOW}║   DiffBot SLAM — Clean Restart Utility   ║${NC}"
echo -e "${YELLOW}╚══════════════════════════════════════════╝${NC}"
echo ""

# ── Step 1: Kill stale processes ──
echo -e "${YELLOW}[1/4]${NC} Killing stale processes..."
killall -9 gzserver gzclient rviz2 robot_state_publisher 2>/dev/null && \
    echo -e "  ${GREEN}✓${NC} Killed leftover Gazebo/RViz/RSP processes" || \
    echo -e "  ${GREEN}✓${NC} No stale processes found"

# ── Step 2: Clean FastRTPS shared memory ──
echo -e "${YELLOW}[2/4]${NC} Cleaning FastRTPS shared memory..."
SHM_COUNT=$(ls /dev/shm/fastrtps_* 2>/dev/null | wc -l)
if [ "$SHM_COUNT" -gt 0 ]; then
    rm -f /dev/shm/fastrtps_*
    echo -e "  ${GREEN}✓${NC} Removed ${SHM_COUNT} stale SHM segments"
else
    echo -e "  ${GREEN}✓${NC} No stale SHM segments found"
fi

# ── Step 3: Restart ROS 2 daemon ──
echo -e "${YELLOW}[3/4]${NC} Restarting ROS 2 daemon..."
ros2 daemon stop  >/dev/null 2>&1 || true
sleep 0.5
ros2 daemon start >/dev/null 2>&1 || true
echo -e "  ${GREEN}✓${NC} ROS 2 daemon restarted"

# ── Step 4: Remove debug artifacts ──
echo -e "${YELLOW}[4/4]${NC} Cleaning debug artifacts..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
rm -f "${SCRIPT_DIR}"/frames_*.gv "${SCRIPT_DIR}"/frames_*.pdf 2>/dev/null
rm -f /tmp/check_clock.py 2>/dev/null
echo -e "  ${GREEN}✓${NC} Debug files cleaned"

echo ""
echo -e "${GREEN}════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Clean slate ready! You can now launch:${NC}"
echo -e "${GREEN}════════════════════════════════════════════${NC}"
echo ""
echo "  Terminal 1:  ros2 launch diffbot_slam simulation.launch.py"
echo "  Terminal 2:  ros2 launch diffbot_slam slam.launch.py"
echo "  Terminal 3:  ros2 run teleop_twist_keyboard teleop_twist_keyboard"
echo ""

# ── Optional: auto-launch ──
if [ "$1" = "--launch" ]; then
    echo -e "${YELLOW}Launching simulation...${NC}"
    cd "${SCRIPT_DIR}"
    # Explicitly force localhost only to bypass firewalls and Wi-Fi cross-talk
    export ROS_DOMAIN_ID=189
    export ROS_LOCALHOST_ONLY=0
    unset FASTRTPS_DEFAULT_PROFILES_FILE   
    source install/setup.bash
    ros2 launch diffbot_slam simulation.launch.py
fi
