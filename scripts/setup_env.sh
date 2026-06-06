#!/bin/bash
# =========================================================
# ZYSTM32-A1 环境设置脚本
# 用法: source scripts/setup_env.sh   (项目根目录下)
# =========================================================

# 自动检测项目根目录（兼容任意安装位置）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
CATKIN_WS="$PROJECT_DIR/ros_ws"

# 1. ROS Noetic 基础环境
if [ -f /opt/ros/noetic/setup.bash ]; then
    source /opt/ros/noetic/setup.bash
else
    echo "❌ 未找到 ROS Noetic，请先安装: sudo apt install ros-noetic-desktop-full"
    return 1 2>/dev/null || exit 1
fi

# 2. catkin 工作区
if [ -f "$CATKIN_WS/devel/setup.bash" ]; then
    source "$CATKIN_WS/devel/setup.bash"
else
    echo "⚠️  catkin 工作区未编译，正在自动编译..."
    (cd "$CATKIN_WS" && catkin_make) && source "$CATKIN_WS/devel/setup.bash"
fi

echo "✅ ZYSTM32-A1 环境已就绪"
echo "   项目目录: $PROJECT_DIR"
echo "   工作空间: $CATKIN_WS"
echo ""
echo "   快捷命令:"
echo "     bash scripts/run.sh                    # 交互式菜单"
echo "     roslaunch orbbec_gemini_slam zystm32_slam.launch   # SLAM"
echo "     cd firmware/USER && make flash         # 烧录固件"
