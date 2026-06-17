import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, SetEnvironmentVariable
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


# ── FastDDS: disable SHM transport to prevent stale messages from prior sessions ──
os.environ.setdefault(
    'FASTRTPS_DEFAULT_PROFILES_FILE',
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'config', 'fastdds_no_shm.xml'
    )
)


def generate_launch_description():
    pkg = get_package_share_directory('diffbot_slam')
    slam_params = os.path.join(pkg, 'config', 'slam_toolbox_params.yaml')

    use_sim_time = LaunchConfiguration('use_sim_time', default='true')

    fastdds_profile = os.path.join(pkg, 'config', 'fastdds_no_shm.xml')

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true',
                              description='Use simulation clock'),

        SetEnvironmentVariable('FASTRTPS_DEFAULT_PROFILES_FILE', fastdds_profile),

        Node(
            package='slam_toolbox',
            executable='async_slam_toolbox_node',
            name='slam_toolbox',
            parameters=[slam_params, {'use_sim_time': use_sim_time}],
            output='screen',
        ),
    ])
