#!/bin/bash
# =========================================================
# ZYSTM32-A1 一键启动
# =========================================================

PROJECT_DIR="$HOME/桌面/ZYSTM32-A1"

echo "================================================"
echo "  ZYSTM32-A1 SLAM 一键启动"
echo "================================================"
echo ""
echo "启动项："
echo "  1. ROS Master (roscore)"
echo "  2. STM32 串口桥接 (/cmd_vel → 串口)"
echo "  3. D435 相机驱动"
echo "  4. RTAB-Map RGB-D SLAM + RViz"
echo "  5. 键盘遥控 (WASDQE)"
echo ""

# Source environment
source "$PROJECT_DIR/scripts/setup_env.sh"

# Start roscore if not running
if ! pgrep -x roscore > /dev/null 2>&1; then
    echo "▶ 启动 roscore..."
    roscore &
    sleep 3
fi

# Launch everything
roslaunch orbbec_gemini_slam zystm32_slam.launch
