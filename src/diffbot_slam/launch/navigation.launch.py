import os
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument, SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
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
    pkg     = get_package_share_directory('diffbot_slam')
    nav2_pkg = get_package_share_directory('nav2_bringup')
    nav2_params = os.path.join(pkg, 'config', 'nav2_params.yaml')

    use_sim_time = LaunchConfiguration('use_sim_time', default='true')

    fastdds_profile = os.path.join(pkg, 'config', 'fastdds_no_shm.xml')

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true',
                              description='Use simulation clock'),

        SetEnvironmentVariable('FASTRTPS_DEFAULT_PROFILES_FILE', fastdds_profile),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(nav2_pkg, 'launch', 'navigation_launch.py')
            ),
            launch_arguments={
                'use_sim_time': 'true',
                'params_file': nav2_params,
            }.items(),
        ),
    ])
