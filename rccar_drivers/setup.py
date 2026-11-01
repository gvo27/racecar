from setuptools import find_packages, setup

package_name = 'rccar_drivers'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/rccar_drivers']),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='gvo27',
    maintainer_email='gvo@berkeley.edu',
    description='Sensor drivers (Slamtec Mapper lidar) for the rccar platform.',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'mapper_driver = rccar_drivers.mapper_node:main',
        ],
    },
)
