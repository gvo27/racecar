cmake_minimum_required(VERSION 3.8)
project(rccar_msgs)

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(builtin_interfaces REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/DriveCmd.msg"
  "msg/Telemetry.msg"
  "msg/McuEvent.msg"
  "msg/SupervisorState.msg"
  "srv/McuCommand.srv"
  "srv/Reset.srv"
  "srv/SetParam.srv"
  "srv/CalPoint.srv"
  "srv/RawPwm.srv"
  DEPENDENCIES builtin_interfaces
)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
