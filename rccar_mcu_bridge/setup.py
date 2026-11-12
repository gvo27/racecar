from setuptools import find_packages, setup

package_name = 'rccar_mcu_bridge'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/rccar_mcu_bridge']),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='gvo27',
    maintainer_email='gvo@berkeley.edu',
    description='Lifecycle bridge: typed services and tuning push for the MCU.',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'mcu_bridge_node = rccar_mcu_bridge.bridge_node:main',
        ],
    },
)
