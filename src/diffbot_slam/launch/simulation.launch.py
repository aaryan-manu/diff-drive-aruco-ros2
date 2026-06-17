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
            'extra_gazebo_args': '--ros-args -p publish_rate:=200.0',
        }.items()
    )

    # ── Robot State Publisher ──
    # Delayed to start AFTER Gazebo so /clock is already publishing
    # when RSP begins using sim time.
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
    # Give Gazebo 3s to fully start and begin publishing /clock
    delayed_rsp = TimerAction(period=3.0, actions=[robot_state_pub])

    # ── Spawn Entity ──
    # Delayed 6s total (after RSP is up) so robot_description topic exists
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
    delayed_spawn = TimerAction(period=6.0, actions=[spawn])

    # ── ArUco Detector (starts after spawn completes) ──
    aruco_detector = Node(
        package='diffbot_slam',
        executable='aruco_detector',
        name='aruco_detector',
        output='screen',
        parameters=[{'use_sim_time': True}],
    )

    # ── RViz ──
    # Delayed 10s after spawn so Gazebo physics clock is fully stable
    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_file],
        parameters=[{'use_sim_time': True}],
        output='screen',
    )
    delayed_rviz = TimerAction(period=10.0, actions=[rviz])

    # After spawn finishes: start aruco detector, schedule RViz
    after_spawn = RegisterEventHandler(
        OnProcessExit(
            target_action=spawn,
            on_exit=[aruco_detector, delayed_rviz],
        )
    )

    return LaunchDescription([
        set_gazebo_model_path,
        set_gazebo_model_database_uri,
        gazebo,
        delayed_rsp,
        delayed_spawn,
        after_spawn,
    ])
