from setuptools import find_packages, setup

package_name = 'rccar_bringup'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/rccar_bringup']),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/car.launch.py']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='gvo27',
    maintainer_email='gvo@berkeley.edu',
    description='Launch files and tuning.toml to ROS parameter mapping.',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
        ],
    },
)
