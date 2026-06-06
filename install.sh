#!/bin/bash
# =============================================================
#  ZYSTM32-A1 一键部署脚本
#  用法: bash install.sh
#
#  功能:
#    1. 检查并安装系统依赖 (ROS, 工具链, Python包)
#    2. 编译 STM32 固件
#    3. 编译 ROS catkin 工作区
#    4. 验证所有组件
# =============================================================

set -e

# ── 颜色 ──────────────────────────────────────────────
RED='\033[0;31m'; GRN='\033[0;32m'; YLW='\033[1;33m'
CYN='\033[0;36m'; NC='\033[0m'; BOLD='\033[1m'

info()  { echo -e "${CYN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GRN}[ OK ]${NC}  $*"; }
warn()  { echo -e "${YLW}[WARN]${NC}  $*"; }
fail()  { echo -e "${RED}[FAIL]${NC} $*"; }

# ── 项目根目录 ────────────────────────────────────────
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
FIRMWARE_DIR="$PROJECT_DIR/firmware/USER"
CATKIN_WS="$PROJECT_DIR/ros_ws"

echo ""
echo -e "${BOLD}${CYN}============================================================${NC}"
echo -e "${BOLD}${CYN}  ZYSTM32-A1 一键部署${NC}"
echo -e "${BOLD}${CYN}  项目目录: $PROJECT_DIR${NC}"
echo -e "${BOLD}${CYN}============================================================${NC}"
echo ""

# ============================================================
# 1. 系统依赖检查
# ============================================================
info "检查系统依赖..."

MISSING=()

# ROS Noetic
if [ -f /opt/ros/noetic/setup.bash ]; then
    ok "ROS Noetic"
    source /opt/ros/noetic/setup.bash
else
    fail "ROS Noetic 未安装"
    MISSING+=("ros-noetic-desktop-full")
fi

# ARM 工具链
if command -v arm-none-eabi-gcc &>/dev/null; then
    ok "arm-none-eabi-gcc $(arm-none-eabi-gcc --version | head -1 | grep -oP '[\d.]+')"
else
    fail "arm-none-eabi-gcc 未安装"
    MISSING+=("gcc-arm-none-eabi")
fi

# stm32flash
if command -v stm32flash &>/dev/null; then
    ok "stm32flash"
else
    fail "stm32flash 未安装"
    MISSING+=("stm32flash")
fi

# Python3 + pyserial
if python3 -c "import serial" 2>/dev/null; then
    ok "pyserial"
else
    fail "pyserial 未安装"
    MISSING+=("pyserial")
fi

# ROS 包检查
check_ros_pkg() {
    if rospack find "$1" &>/dev/null; then
        ok "ros-noetic-$(echo $1 | tr '_' '-')"
    else
        fail "$1 未安装"
        MISSING+=("ros-noetic-$(echo $1 | tr '_' '-')")
    fi
}

if [ -f /opt/ros/noetic/setup.bash ]; then
    check_ros_pkg "rtabmap_ros"
    check_ros_pkg "realsense2_camera"
    check_ros_pkg "explore_lite"
    check_ros_pkg "move_base"
    check_ros_pkg "depthimage_to_laserscan"
fi

# 安装缺失包
if [ ${#MISSING[@]} -gt 0 ]; then
    echo ""
    warn "发现缺失依赖，尝试自动安装..."
    echo ""

    # 分离 apt 包和 pip 包
    APT_PKGS=()
    PIP_PKGS=()
    for pkg in "${MISSING[@]}"; do
        if [ "$pkg" = "pyserial" ]; then
            PIP_PKGS+=("pyserial")
        elif [ "$pkg" = "gcc-arm-none-eabi" ]; then
            APT_PKGS+=("gcc-arm-none-eabi" "binutils-arm-none-eabi")
        elif [ "$pkg" = "stm32flash" ]; then
            APT_PKGS+=("stm32flash")
        else
            APT_PKGS+=("$pkg")
        fi
    done

    if [ ${#APT_PKGS[@]} -gt 0 ]; then
        info "安装 APT 包: ${APT_PKGS[*]}"
        sudo apt install -y "${APT_PKGS[@]}" || warn "部分 APT 包安装失败，请手动安装"
    fi

    if [ ${#PIP_PKGS[@]} -gt 0 ]; then
        info "安装 Python 包: ${PIP_PKGS[*]}"
        pip3 install "${PIP_PKGS[@]}" || warn "pip 安装失败，请手动: pip3 install ${PIP_PKGS[*]}"
    fi

    # 重新 source
    [ -f /opt/ros/noetic/setup.bash ] && source /opt/ros/noetic/setup.bash
fi

echo ""

# ============================================================
# 2. 编译 STM32 固件
# ============================================================
info "编译 STM32 固件..."

if command -v arm-none-eabi-gcc &>/dev/null; then
    cd "$FIRMWARE_DIR"
    make clean > /dev/null 2>&1
    if make all 2>&1 | tail -5; then
        SIZE=$(arm-none-eabi-size zystm32_a1_slam.elf 2>/dev/null | tail -1 | awk '{print $1}')
        ok "固件编译成功 (${SIZE} bytes text)"
    else
        fail "固件编译失败"
    fi
else
    warn "跳过固件编译（缺少 arm-none-eabi-gcc）"
fi

echo ""

# ============================================================
# 3. 编译 ROS 工作区
# ============================================================
info "编译 ROS catkin 工作区..."

if [ -f /opt/ros/noetic/setup.bash ]; then
    source /opt/ros/noetic/setup.bash
    cd "$CATKIN_WS"
    if catkin_make 2>&1 | tail -5; then
        ok "catkin_make 成功"
    else
        fail "catkin_make 失败"
    fi
else
    warn "跳过 ROS 编译（缺少 ROS Noetic）"
fi

echo ""

# ============================================================
# 4. 验证
# ============================================================
info "验证部署..."

PASS=true

[ -f "$FIRMWARE_DIR/zystm32_a1_slam.bin" ] && ok "固件 .bin" || { fail "固件 .bin"; PASS=false; }
[ -f "$CATKIN_WS/devel/setup.bash" ]       && ok "ROS devel" || { fail "ROS devel"; PASS=false; }
[ -f "$CATKIN_WS/devel/lib/orbbec_gemini_slam/stm32_serial_bridge.py" ] && ok "桥接节点" || { fail "桥接节点"; PASS=false; }
[ -f "$CATKIN_WS/devel/lib/orbbec_gemini_slam/keyboard_teleop.py" ]     && ok "键盘遥控" || { fail "键盘遥控"; PASS=false; }

echo ""
echo -e "${BOLD}============================================================${NC}"
if $PASS; then
    echo -e "${BOLD}${GRN}  ✅ 部署完成！${NC}"
else
    echo -e "${BOLD}${YLW}  ⚠️  部分组件有问题，请检查上面的红色项${NC}"
fi
echo -e "${BOLD}============================================================${NC}"
echo ""
echo "  下一步:"
echo ""
echo "  1. 烧录固件:"
echo "     cd firmware/USER && make flash"
echo ""
echo "  2. 测试串口:"
echo "     screen /dev/ttyUSB0 115200    # 敲 H 回车"
echo ""
echo "  3. 一键启动 SLAM:"
echo "     bash scripts/run.sh           # 交互式菜单"
echo ""
echo "  4. 或直接启动:"
echo "     source scripts/setup_env.sh"
echo "     roslaunch orbbec_gemini_slam zystm32_slam.launch"
echo ""
