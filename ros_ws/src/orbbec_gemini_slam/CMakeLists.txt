cmake_minimum_required(VERSION 2.8.3)
project(orbbec_gemini_slam)

find_package(catkin REQUIRED COMPONENTS
  rospy
  sensor_msgs
  geometry_msgs
  std_msgs
  cv_bridge
  image_transport
)

catkin_package()

# 安装 Python 脚本
catkin_install_python(PROGRAMS
  scripts/orbbec_stereo_node.py
  scripts/calibrate_stereo.py
  scripts/stm32_serial_bridge.py
  scripts/keyboard_teleop.py
  scripts/simple_explorer.py
  scripts/print_ultrasonic.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

# 安装 launch 文件
install(DIRECTORY launch/
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}/launch
)

# 安装测试脚本
install(PROGRAMS
  scripts/zystm32_auto_test.sh
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

# 安装 config 文件
install(DIRECTORY config/
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}/config
  FILES_MATCHING
  PATTERN "*.yaml"
  PATTERN "*.rviz"
)
