#!/usr/bin/env bash
# ============================================================================
# install_deps.sh — Install all dependencies for diffbot_slam from scratch
# Targets: Ubuntu 22.04 (Jammy) + ROS 2 Humble
# Usage:   chmod +x install_deps.sh && ./install_deps.sh
# ============================================================================

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

log()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC}  $*"; }
err()  { echo -e "${RED}[ERR]${NC}   $*"; }

# ── 0. Pre-flight checks ───────────────────────────────────────────────────
if [[ "$(lsb_release -cs 2>/dev/null)" != "jammy" ]]; then
    err "This script targets Ubuntu 22.04 (Jammy). Detected: $(lsb_release -ds 2>/dev/null || echo 'unknown')"
    exit 1
fi

log "Starting full dependency installation for diffbot_slam..."

# ── 1. System essentials ───────────────────────────────────────────────────
log "Installing system essentials..."
sudo apt-get update
sudo apt-get install -y \
    software-properties-common \
    curl \
    gnupg \
    lsb-release \
    build-essential \
    python3-pip \
    python3-colcon-common-extensions \
    python3-rosdep \
    git \
    wget

# ── 2. ROS 2 Humble ───────────────────────────────────────────────────────
if ! dpkg -l | grep -q "ros-humble-desktop"; then
    log "Adding ROS 2 Humble repository..."

    # Add the ROS 2 GPG key
    sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
        -o /usr/share/keyrings/ros-archive-keyring.gpg

    # Add the repository
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] \
http://packages.ros.org/ros2/ubuntu $(lsb_release -cs) main" | \
        sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

    sudo apt-get update

    log "Installing ROS 2 Humble Desktop (this may take a while)..."
    sudo apt-get install -y ros-humble-desktop
else
    log "ROS 2 Humble Desktop already installed — skipping."
fi

# ── 3. ROS 2 packages required by diffbot_slam ────────────────────────────
log "Installing required ROS 2 packages..."
sudo apt-get install -y \
    ros-humble-gazebo-ros-pkgs \
    ros-humble-robot-state-publisher \
    ros-humble-joint-state-publisher \
    ros-humble-xacro \
    ros-humble-slam-toolbox \
    ros-humble-nav2-bringup \
    ros-humble-teleop-twist-keyboard \
    ros-humble-cv-bridge \
    ros-humble-image-transport \
    ros-humble-tf2-ros \
    ros-humble-rviz2

# ── 4. Python dependencies ────────────────────────────────────────────────
log "Installing Python packages..."
pip3 install --user \
    "opencv-contrib-python<4.9" \
    "numpy<2"

# ── 5. Initialise rosdep (if not already) ─────────────────────────────────
if [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then
    log "Initialising rosdep..."
    sudo rosdep init || true
fi
rosdep update --rosdistro=humble || true

# ── 6. Source ROS 2 in current shell & add to bashrc ──────────────────────
ROS_SETUP="/opt/ros/humble/setup.bash"
if ! grep -q "source ${ROS_SETUP}" ~/.bashrc; then
    log "Adding ROS 2 source to ~/.bashrc..."
    echo "" >> ~/.bashrc
    echo "# ROS 2 Humble" >> ~/.bashrc
    echo "source ${ROS_SETUP}" >> ~/.bashrc
fi

# ── 7. Build the workspace ────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
log "Building workspace at ${SCRIPT_DIR}..."

# shellcheck disable=SC1091
source "${ROS_SETUP}"

cd "${SCRIPT_DIR}"
rosdep install --from-paths src --ignore-src -r -y || true
colcon build --symlink-install

# Source the workspace overlay
WS_SETUP="${SCRIPT_DIR}/install/setup.bash"
if ! grep -q "source ${WS_SETUP}" ~/.bashrc; then
    log "Adding workspace source to ~/.bashrc..."
    echo "source ${WS_SETUP}" >> ~/.bashrc
fi

echo ""
log "============================================"
log "  Installation complete!"
log "============================================"
log ""
log "Open a NEW terminal, then run:"
log "  ros2 launch diffbot_slam simulation.launch.py"
log ""
