"""
Car bringup: supervisor + lifecycle mcu_bridge (auto configure/activate).

Launch arguments:
  use_sim_time    pass-through to every node (default false)
  sim             true = skip MCU-facing nodes; the sim adapter lives in the sim repo
  tuning_file     tuning.toml (default: $RCCAR_TUNING or /ws/src/racecar/tuning.toml)
  heartbeat_dir   directory for docker healthcheck files (default '' = disabled)
"""
import os

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument, EmitEvent, LogInfo, OpaqueFunction, RegisterEventHandler)
from launch.event_handlers import OnProcessStart
from launch.events import matches_action
from launch.substitutions import EnvironmentVariable, LaunchConfiguration
from launch_ros.actions import LifecycleNode, Node
from launch_ros.event_handlers import OnStateTransition
from launch_ros.events.lifecycle import ChangeState
from lifecycle_msgs.msg import Transition
from rccar_bringup.tuning_params import node_params
import tomllib


def _truthy(value: str) -> bool:
    return str(value).strip().lower() in ('1', 'true', 'yes', 'on')


def _setup(context):
    use_sim_time = _truthy(LaunchConfiguration('use_sim_time').perform(context))
    sim = _truthy(LaunchConfiguration('sim').perform(context))
    tuning_file = LaunchConfiguration('tuning_file').perform(context)
    hb_dir = LaunchConfiguration('heartbeat_dir').perform(context)

    actions = []
    params = {'supervisor': {}, 'mcu_bridge': {}}
    try:
        with open(tuning_file, 'rb') as f:
            params = node_params(tomllib.load(f))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        actions.append(LogInfo(msg=f'WARNING: cannot read tuning {tuning_file}: {exc}; '
                                   'nodes use code defaults'))

    def common(name):
        p = dict(params[name])
        p['use_sim_time'] = use_sim_time
        if hb_dir:
            p['heartbeat_file'] = os.path.join(hb_dir, name)
        return p

    actions.append(Node(package='rccar_supervisor', executable='supervisor_node',
                        name='supervisor', output='screen',
                        parameters=[common('supervisor')]))

    if sim:
        actions.append(LogInfo(msg='sim:=true: sim adapter lives in the sim repo; '
                                   'skipping mcu_bridge'))
        return actions

    bridge_params = common('mcu_bridge')
    bridge_params['tuning_file'] = tuning_file
    bridge = LifecycleNode(package='rccar_mcu_bridge', executable='mcu_bridge_node',
                           name='mcu_bridge', namespace='', output='screen',
                           parameters=[bridge_params])
    actions.append(bridge)
    # unconfigured -> configure on process start; inactive -> activate.
    actions.append(RegisterEventHandler(OnProcessStart(
        target_action=bridge,
        on_start=[EmitEvent(event=ChangeState(
            lifecycle_node_matcher=matches_action(bridge),
            transition_id=Transition.TRANSITION_CONFIGURE))])))
    actions.append(RegisterEventHandler(OnStateTransition(
        target_lifecycle_node=bridge, goal_state='inactive',
        entities=[EmitEvent(event=ChangeState(
            lifecycle_node_matcher=matches_action(bridge),
            transition_id=Transition.TRANSITION_ACTIVATE))])))
    return actions


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='false',
                              description='use /clock (simulation) for every node'),
        DeclareLaunchArgument('sim', default_value='false',
                              description='true: skip MCU-facing nodes (sim adapter replaces '
                                          'them, lives in the sim repo)'),
        DeclareLaunchArgument(
            'tuning_file',
            default_value=EnvironmentVariable(
                'RCCAR_TUNING', default_value='/ws/src/racecar/tuning.toml'),
            description='tuning.toml loaded into node parameters and pushed to the MCU'),
        DeclareLaunchArgument('heartbeat_dir', default_value='',
                              description='directory for docker healthcheck heartbeat '
                                          'files (empty = disabled)'),
        OpaqueFunction(function=_setup),
    ])
