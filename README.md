# DiffBot SLAM Workspace (diff-drive-aruco-ros2)

A ROS 2 Humble differential-drive robot simulation with **ArUco marker detection**, **SLAM Toolbox** mapping, and **Nav2 navigation** — all running in Gazebo Classic.

## Features

- **Differential-drive robot** with LiDAR + RGB camera (URDF/Xacro)
- **ArUco marker detection** — detects 4X4_50 markers and publishes poses + TF
- **ArUco command follower** — the robot autonomously follows movement commands encoded as markers
- **SLAM Toolbox integration** — build a 2D occupancy grid map of the environment
- **Nav2 navigation** — autonomous path planning and obstacle avoidance
- **Gazebo simulation world** — enclosed arena with obstacles and ArUco markers on the walls
- **RViz2 visualisation** — pre-configured to show robot model, LiDAR, map, camera, and ArUco detections

---

## Installation (From Scratch)

> Targets **Ubuntu 22.04 (Jammy)** + **ROS 2 Humble**

### Option A — Automated (recommended)

```bash
git clone https://github.com/aaryan-manu/diff-drive-aruco-ros2.git ~/diffbot_slam_ws
cd ~/diffbot_slam_ws
chmod +x install_deps.sh
./install_deps.sh
```

This single script installs ROS 2 Humble, Gazebo, all ROS/Python dependencies, and builds the workspace.

### Option B — Manual step-by-step

#### 1. Install ROS 2 Humble

```bash
# Add ROS 2 GPG key
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
    -o /usr/share/keyrings/ros-archive-keyring.gpg

# Add the repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] \
http://packages.ros.org/ros2/ubuntu $(lsb_release -cs) main" | \
    sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

# Install
sudo apt update
sudo apt install -y ros-humble-desktop
```

#### 2. Install required ROS 2 packages

```bash
sudo apt install -y \
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
```

#### 3. Install build tools & Python dependencies

```bash
sudo apt install -y \
    python3-pip \
    python3-colcon-common-extensions \
    python3-rosdep \
    build-essential

pip3 install --user opencv-contrib-python numpy
```

#### 4. Initialise rosdep

```bash
sudo rosdep init          # skip if already done
rosdep update --rosdistro=humble
```

#### 5. Clone and Build the workspace

```bash
git clone https://github.com/aaryan-manu/diff-drive-aruco-ros2.git ~/diffbot_slam_ws
source /opt/ros/humble/setup.bash
cd ~/diffbot_slam_ws
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
```

#### 6. Source the workspace

```bash
# Add to ~/.bashrc so it's always available:
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
echo "source ~/diffbot_slam_ws/install/setup.bash" >> ~/.bashrc
source ~/.bashrc
```

---

## Network Isolation (Shared Wi-Fi)

> [!WARNING]
> **Important for Classrooms / Shared Networks:** If your classmates are running this simulation on the same Wi-Fi, your robots will cross-talk, causing massive time jumps and erratic behavior!

To completely isolate your robot from the classroom network, this workspace uses a custom domain ID: **`ROS_DOMAIN_ID=189`**.

This completely bypasses Wi-Fi cross-talk with other students. This has been automatically added to your `~/.bashrc` and is enforced by the helper scripts.

## Quick Start (Foolproof Method)

To avoid any issues with terminal environments or shared memory, use the provided launch scripts. These scripts automatically isolate your network to Domain 189, clean stale processes, and launch the modules **in a single terminal**.

### 1. Manual Teleop
```bash
cd ~/diffbot_slam_ws
./run_all.sh
```
*(Teleop will run directly in this terminal. Press `q` to exit, which will automatically safely shut down Gazebo and SLAM).*

### 2. Auto-Navigation & Semantic Patrol
```bash
cd ~/diffbot_slam_ws
./run_nav.sh
```
*(This launches Gazebo, SLAM, Nav2, and the autonomous Semantic Visual Patrol node. You can provide goals via RViz or let ArUco markers guide the robot).*

### Manual Launch (Alternative)
If you prefer to launch things manually, open fresh terminals and ensure `export ROS_DOMAIN_ID=189` is active:

**Terminal 1:** `ros2 launch diffbot_slam simulation.launch.py`
**Terminal 2:** `ros2 launch diffbot_slam slam.launch.py`
source install/setup.bash
ros2 launch diffbot_slam navigation.launch.py
```

---

## Save & Load Maps

**Save the current map:**
```bash
cd ~/diffbot_slam_ws
source install/setup.bash
ros2 run nav2_map_server map_saver_cli -f src/diffbot_slam/maps/my_map
```

**Load a saved map (for navigation without SLAM):**
```bash
ros2 run nav2_map_server map_server --ros-args -p yaml_filename:=src/diffbot_slam/maps/my_map.yaml -p use_sim_time:=true
ros2 run nav2_util lifecycle_bringup map_server
```

---

## ArUco Marker Command Mapping

| Marker ID | Command   | Velocity                  |
|-----------|-----------|---------------------------|
| 1         | Turn Left | `angular.z = +0.5 rad/s`  |
| 2         | Turn Right| `angular.z = -0.5 rad/s`  |
| 3         | Forward   | `linear.x  = +0.2 m/s`   |
| 4         | Backward  | `linear.x  = -0.2 m/s`   |

When no marker is detected, the robot stops (all velocities = 0).

---

## Project Structure

```
diffbot_slam_ws/
├── install_deps.sh                   ← One-command installer
├── clean_restart.sh                  ← Kill stale processes & clean SHM before relaunching
├── README.md
└── src/
    └── diffbot_slam/
        ├── package.xml
        ├── setup.py
        ├── setup.cfg
        ├── urdf/
        │   └── diffbot.urdf.xacro    ← Robot model (base + wheels + LiDAR + camera)
        ├── worlds/
        │   └── aruco_world.world      ← Gazebo world with walls, obstacles & markers
        ├── models/
        │   ├── aruco_marker/          ← Generic marker template
        │   ├── aruco_marker_1/        ← ID 1 — Turn Left
        │   ├── aruco_marker_2/        ← ID 2 — Turn Right
        │   ├── aruco_marker_3/        ← ID 3 — Forward
        │   └── aruco_marker_4/        ← ID 4 — Backward
        ├── launch/
        │   ├── simulation.launch.py   ← Gazebo + robot + RViz + ArUco detector
        │   ├── slam.launch.py         ← SLAM Toolbox async node
        │   └── navigation.launch.py   ← Nav2 stack bringup
        ├── config/
        │   ├── rviz_config.rviz       ← RViz display layout
        │   ├── slam_toolbox_params.yaml
        │   ├── nav2_params.yaml
        │   └── fastdds_no_shm.xml    ← FastDDS profile: disables SHM transport
        ├── maps/
        │   ├── my_map.pgm
        │   └── my_map.yaml
        ├── test/
        │   ├── test_copyright.py
        │   ├── test_flake8.py
        │   └── test_pep257.py
        └── diffbot_slam/
            ├── __init__.py
            ├── aruco_detector.py      ← ArUco marker pose estimation node
            └── aruco_command_follower.py  ← Marker-to-velocity mapper node
```

---

## ROS 2 Topics Published

| Topic                | Message Type             | Description                          |
|----------------------|--------------------------|--------------------------------------|
| `/aruco/detections`  | `geometry_msgs/PoseArray`| Detected marker poses in camera frame|
| `/aruco/ids`         | `std_msgs/Int32MultiArray`| List of detected marker IDs         |
| `/aruco/image_debug` | `sensor_msgs/Image`      | Annotated camera feed with markers   |
| `/cmd_vel`           | `geometry_msgs/Twist`    | Velocity commands from follower      |
| `/scan`              | `sensor_msgs/LaserScan`  | 360° LiDAR scan                      |
| `/odom`              | `nav_msgs/Odometry`      | Wheel odometry from diff-drive       |
| `/camera/image_raw`  | `sensor_msgs/Image`      | Raw RGB camera feed                  |
| `/camera/camera_info`| `sensor_msgs/CameraInfo` | Camera intrinsic parameters          |

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Gazebo crashes, port conflicts, or stale processes | Run `./clean_restart.sh` from the workspace root. This kills stale Gazebo/RViz processes, cleans FastRTPS shared memory, and restarts the ROS 2 daemon. |
| RViz shows `TF_OLD_DATA` or "jump back in time" | **Root cause:** This happens either when stale FastRTPS shared memory caches old session messages, OR when another person on your Wi-Fi is running the same simulation. **Fix:** Ensure you use the provided scripts (`run_all.sh` or `run_nav.sh`) to force `ROS_DOMAIN_ID=189` and automatically clear shared memory. |
| SLAM map not appearing / Teleop not moving robot | Your terminals might be out of date. Close all terminals and open a fresh one to ensure the correct domain ID is loaded, or simply use `run_nav.sh`. |
| Nav2 plugins fail to load | Ensure the correct Humble plugin formatting in `nav2_params.yaml` (e.g. `nav2_navfn_planner/NavfnPlanner`). |
| No LiDAR data in RViz | Check Fixed Frame is set to `odom` or `map` in RViz Global Options. |
| ArUco markers not detected | Ensure camera is pointing at a marker; check `/camera/image_raw` topic. The ArUco detector uses modern `cv2.solvePnP` (not the deprecated `estimatePoseSingleMarkers`). |
| `ModuleNotFoundError: cv2` | Run `pip3 install --user opencv-contrib-python` or use `install_deps.sh`. |
| Build fails with missing dependencies | Run `rosdep install --from-paths src --ignore-src -r -y` or run `install_deps.sh`. |
| Teleop not sending commands | Make sure the teleop terminal window is focused while pressing keys. |
| `RTPS_TRANSPORT_SHM Error` in console | Harmless if using the FastDDS no-SHM profile. Run `rm -f /dev/shm/fastrtps_*` to clean up residual segments. |

---

## License

Apache-2.0
