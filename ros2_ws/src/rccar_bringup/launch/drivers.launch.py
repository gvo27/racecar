"""
Sensor drivers: robot_state_publisher + lifecycle mapper_driver (auto configure/activate).

Launch arguments:
  use_sim_time    pass-through to every node (default false)
  heartbeat_dir   directory for docker healthcheck files (default '' = disabled)
  mapper_host     Slamtec Mapper IP (default 192.168.11.1, the Mapper's own AP)
  urdf_file       xacro for robot_state_publisher (default '' = rccar_description
                  rccar.urdf.xacro). The sim repo gives its wrapper xacro, so one
                  robot_state_publisher serves the car frames and the sim model.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument, EmitEvent, OpaqueFunction, RegisterEventHandler)
from launch.event_handlers import OnProcessStart
from launch.events import matches_action
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import LifecycleNode, Node
from launch_ros.event_handlers import OnStateTransition
from launch_ros.events.lifecycle import ChangeState
from launch_ros.parameter_descriptions import ParameterValue
from lifecycle_msgs.msg import Transition


def _truthy(value: str) -> bool:
    return str(value).strip().lower() in ('1', 'true', 'yes', 'on')


def _setup(context):
    use_sim_time = _truthy(LaunchConfiguration('use_sim_time').perform(context))
    hb_dir = LaunchConfiguration('heartbeat_dir').perform(context)
    host = LaunchConfiguration('mapper_host').perform(context)

    xacro_file = LaunchConfiguration('urdf_file').perform(context) or os.path.join(
        get_package_share_directory('rccar_description'), 'urdf', 'rccar.urdf.xacro')
    rsp = Node(package='robot_state_publisher', executable='robot_state_publisher',
               name='robot_state_publisher', output='screen',
               parameters=[{'robot_description': ParameterValue(
                                Command(['xacro ', xacro_file]), value_type=str),
                            'use_sim_time': use_sim_time}])

    params = {'host': host, 'use_sim_time': use_sim_time}
    if hb_dir:
        params['heartbeat_file'] = os.path.join(hb_dir, 'mapper_driver')
    driver = LifecycleNode(package='rccar_drivers', executable='mapper_driver',
                           name='mapper_driver', namespace='', output='screen',
                           parameters=[params])
    return [
        rsp,
        driver,
        # unconfigured -> configure on process start; inactive -> activate.
        RegisterEventHandler(OnProcessStart(
            target_action=driver,
            on_start=[EmitEvent(event=ChangeState(
                lifecycle_node_matcher=matches_action(driver),
                transition_id=Transition.TRANSITION_CONFIGURE))])),
        RegisterEventHandler(OnStateTransition(
            target_lifecycle_node=driver, goal_state='inactive',
            entities=[EmitEvent(event=ChangeState(
                lifecycle_node_matcher=matches_action(driver),
                transition_id=Transition.TRANSITION_ACTIVATE))])),
    ]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='false',
                              description='use /clock (simulation) for every node'),
        DeclareLaunchArgument('heartbeat_dir', default_value='',
                              description='directory for docker healthcheck heartbeat '
                                          'files (empty = disabled)'),
        DeclareLaunchArgument('mapper_host', default_value='192.168.11.1',
                              description='Slamtec Mapper IP address'),
        DeclareLaunchArgument('urdf_file', default_value='',
                              description='xacro file for robot_state_publisher '
                                          '(empty = rccar_description rccar.urdf.xacro)'),
        OpaqueFunction(function=_setup),
    ])
