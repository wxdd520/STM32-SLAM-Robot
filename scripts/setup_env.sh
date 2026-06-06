#!/bin/bash
# =========================================================
# ZYSTM32-A1 环境设置脚本（新版统一路径）
# 用法: source ~/桌面/ZYSTM32-A1/scripts/setup_env.sh
# =========================================================

PROJECT_DIR="$HOME/桌面/ZYSTM32-A1"
CATKIN_WS="$PROJECT_DIR/ros_ws"

# 1. ROS Noetic 基础环境
source /opt/ros/noetic/setup.bash

# 2. catkin 工作区
if [ -f "$CATKIN_WS/devel/setup.bash" ]; then
    source "$CATKIN_WS/devel/setup.bash"
fi

echo "✅ ZYSTM32-A1 环境已就绪"
echo "   workspace: $CATKIN_WS"
echo "   一键启动:  roslaunch orbbec_gemini_slam zystm32_slam.launch"
echo "   烧录固件:  cd $PROJECT_DIR/firmware/USER && make flash"
echo "   串口测试:  python3 $PROJECT_DIR/tools/test_stm32.py"
