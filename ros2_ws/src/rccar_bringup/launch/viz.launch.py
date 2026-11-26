"""
Live websocket feed (foxglove_bridge) for Foxglove / Lichtblick.

The bridge binds to 127.0.0.1 by default: nothing on the network can connect,
only something already on the Pi. The laptop reaches it through an SSH port
forward (VS Code Remote-SSH forwards localhost:8765 automatically), so the
feed inherits SSH authentication instead of exposing an open websocket.
Only car topics, TF, diagnostics and the URDF are served (whitelist).
Read-only for the car: foxglove_bridge defaults enable clientPublish,
services and parameters with '.*' whitelists, which would let a viewer
publish /rccar/mcu/drive (bypassing the supervisor) or call /supervisor/arm.
So capabilities are limited to connectionGraph + assets, and the client-topic,
service and parameter whitelists match nothing (defense in depth).

Usage: ros2 launch rccar_bringup viz.launch.py [port:=8765] [address:=127.0.0.1]
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

TOPIC_WHITELIST = [
    '^/rccar/.*',
    '^/tf$',
    '^/tf_static$',
    '^/diagnostics$',
    '^/robot_description$',
]
# read-only: never add clientPublish / services / parameters (see drivers.md)
CAPABILITIES = ['connectionGraph', 'assets']
NOTHING = ['^$']


def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time')
    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        DeclareLaunchArgument('port', default_value='8765'),
        DeclareLaunchArgument('address', default_value='127.0.0.1'),
        Node(
            package='foxglove_bridge',
            executable='foxglove_bridge',
            name='foxglove_bridge',
            output='screen',
            parameters=[{
                'port': ParameterValue(LaunchConfiguration('port'), value_type=int),
                'address': LaunchConfiguration('address'),
                'topic_whitelist': TOPIC_WHITELIST,
                'capabilities': CAPABILITIES,
                'client_topic_whitelist': NOTHING,
                'service_whitelist': NOTHING,
                'param_whitelist': NOTHING,
                'use_sim_time': ParameterValue(use_sim_time, value_type=bool),
            }],
        ),
    ])
