from setuptools import setup, find_packages
import os
from glob import glob

package_name = 'diffbot_slam'


def get_data_files():
    data_files = [
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'),
            glob('launch/*.py')),
        (os.path.join('share', package_name, 'urdf'),
            glob('urdf/*')),
        (os.path.join('share', package_name, 'worlds'),
            glob('worlds/*')),
        (os.path.join('share', package_name, 'config'),
            glob('config/*')),
        (os.path.join('share', package_name, 'maps'),
            glob('maps/*')),
    ]
    # Dynamically grab all model files (including subdirectories like materials/textures)
    for path, _, files in os.walk('models'):
        install_dir = os.path.join('share', package_name, path)
        file_list = [os.path.join(path, f) for f in files]
        if file_list:
            data_files.append((install_dir, file_list))
    return data_files


setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=get_data_files(),
    install_requires=['setuptools'],
    zip_safe=True,
    author='Your Name',
    author_email='you@example.com',
    description='Differential drive robot with ArUco + SLAM Toolbox',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'aruco_detector = diffbot_slam.aruco_detector:main',
            'aruco_command_follower = diffbot_slam.aruco_command_follower:main',
        ],
    },
)
