#!/bin/bash
# 快速测试 ROS → STM32 通信
# 自动 source 环境，通过 systemd-run --user 绕过 /dev/ttyUSB0 命名空间隔离

source /opt/ros/noetic/setup.bash
# 新项目位置:
source ~/桌面/ZYSTM32-A1/ros_ws/devel/setup.bash 2>/dev/null
# 旧位置兼容:
# source ~/桌面/Slam/catkin_ws/devel/setup.bash 2>/dev/null

echo "==================== ROS → STM32 测试 ===================="
echo ""
echo "  新固件 (SONIC+ROS)："
echo "  · 默认 AUTO 模式 (超声波舵机扫描避障)"
echo "  · ROS 发指令 → 自动切 MANUAL"
echo "  · 3s 无 ROS 指令 → 回到 AUTO"
echo ""
echo "=========================================================="
echo ""

export ROS_MASTER_URI=${ROS_MASTER_URI:-http://localhost:11311}

exec systemd-run --user --pty --same-dir --collect \
    --setenv="ROS_MASTER_URI=$ROS_MASTER_URI" \
    --setenv="ROS_ROOT=$ROS_ROOT" \
    --setenv="ROS_PACKAGE_PATH=$ROS_PACKAGE_PATH" \
    --setenv="PYTHONPATH=$PYTHONPATH" \
    --setenv="LD_LIBRARY_PATH=$LD_LIBRARY_PATH" \
    --setenv="PATH=$PATH" \
    --setenv="HOME=$HOME" \
    rosrun orbbec_gemini_slam stm32_serial_bridge.py _port:=/dev/ttyUSB0
