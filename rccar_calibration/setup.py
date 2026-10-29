from setuptools import find_packages, setup

package_name = 'rccar_calibration'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/rccar_calibration']),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='gvo27',
    maintainer_email='gvo@berkeley.edu',
    description='Interactive calibration, bench test and tuning CLIs.',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'calibrate = rccar_calibration.calibrate:main',
            'bench_test = rccar_calibration.bench_test:main',
            'tune = rccar_calibration.tune:main',
        ],
    },
)
