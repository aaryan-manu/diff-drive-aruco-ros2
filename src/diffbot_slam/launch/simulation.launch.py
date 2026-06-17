import os
from launch import LaunchDescription
from launch.actions import (IncludeLaunchDescription, TimerAction,
                             RegisterEventHandler, SetEnvironmentVariable)
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import xacro


def generate_launch_description():
    pkg_share = get_package_share_directory('diffbot_slam')

    world_file = os.path.join(pkg_share, 'worlds', 'aruco_world.world')
    xacro_file = os.path.join(pkg_share, 'urdf', 'diffbot.urdf.xacro')
    rviz_file  = os.path.join(pkg_share, 'config', 'rviz_config.rviz')

    doc = xacro.process_file(xacro_file)
    robot_desc = doc.toxml()

    # Tell Gazebo where to find our custom ArUco marker models
    models_path = os.path.join(pkg_share, 'models')
    set_gazebo_model_path = SetEnvironmentVariable(
        'GAZEBO_MODEL_PATH',
        models_path + ':' + os.environ.get('GAZEBO_MODEL_PATH', '')
    )

    # Disable online model database lookup to prevent Gazebo from hanging on startup
    set_gazebo_model_database_uri = SetEnvironmentVariable(
        'GAZEBO_MODEL_DATABASE_URI',
        ''
    )

    # ── Gazebo ──
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            os.path.join(
                get_package_share_directory('gazebo_ros'),
                'launch', 'gazebo.launch.py')
        ]),
        launch_arguments={
            'world': world_file,
            'verbose': 'true',
        }.items()
    )

    # ── Robot State Publisher ──
    robot_state_pub = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'use_sim_time': True,
            'robot_description': robot_desc,
        }],
    )

    # ── Spawn Entity (delayed 5s to let Gazebo start) ──
    spawn = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=[
            '-entity', 'diffbot',
            '-topic', 'robot_description',
            '-x', '0.0', '-y', '0.0', '-z', '0.04',
            '-timeout', '60',
        ],
        output='screen'
    )
    delayed_spawn = TimerAction(period=5.0, actions=[spawn])

    # ── ArUco Detector (starts after spawn completes) ──
    aruco_detector = Node(
        package='diffbot_slam',
        executable='aruco_detector',
        name='aruco_detector',
        output='screen',
        parameters=[{'use_sim_time': True}],
    )

    # ── RViz (starts after spawn completes) ──
    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_file],
        parameters=[{'use_sim_time': True}],
        output='screen',
    )

    # Start aruco_detector and rviz only after spawn_entity finishes
    after_spawn = RegisterEventHandler(
        OnProcessExit(
            target_action=spawn,
            on_exit=[aruco_detector, rviz],
        )
    )

    return LaunchDescription([
        set_gazebo_model_path,
        set_gazebo_model_database_uri,
        gazebo,
        robot_state_pub,
        delayed_spawn,
        after_spawn,
    ])
