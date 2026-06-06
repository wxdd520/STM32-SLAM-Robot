#!/bin/bash
# ============================================================
# stm32_auto_test.sh — STM32-SLAM-Robot 全自主探索 测试脚本 V2
# ============================================================
# 分工会作模式：ROS 做 SLAM + 探索决策，STM32 做底层安全避障
# 
# 用法:
#   ./stm32_auto_test.sh              # 全自主探索+建图 (V2)
#   ./stm32_auto_test.sh check        # 仅检查环境（不启动）
#   ./stm32_auto_test.sh keyboard     # 手动建图模式（带键盘）
# ============================================================

set -e

RED='\033[0;31m'
GRN='\033[0;32m'
YLW='\033[1;33m'
CYN='\033[0;36m'
NC='\033[0m'
BOLD='\033[1m'

info()  { echo -e "${CYN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GRN}[ OK ]${NC}  $*"; }
warn()  { echo -e "${YLW}[WARN]${NC}  $*"; }
fail()  { echo -e "${RED}[FAIL]${NC} $*"; }
header(){ echo -e "\n${BOLD}${CYN}=== $* ===${NC}\n"; }

MODE="${1:-explore}"

header "STM32-SLAM-Robot 全自主探索 V2（分工会作模式）"

# ============================================================
# 1. 环境检查
# ============================================================
info "检查系统环境..."

if [ -z "$ROS_DISTRO" ]; then
    if [ -f /opt/ros/noetic/setup.bash ]; then
        source /opt/ros/noetic/setup.bash
        ok "已加载 ROS 环境"
    else
        fail "未找到 ROS 环境"
        exit 1
    fi
else
    ok "ROS $ROS_DISTRO"
fi

# V2 只需要这些包
check_pkg() {
    if dpkg -l "ros-noetic-$1" &>/dev/null; then
        ok "ros-noetic-$1"
        return 0
    else
        fail "ros-noetic-$1 未安装"
        MISSING+=("ros-noetic-$1")
        return 1
    fi
}

MISSING=()
set +e
check_pkg "rtabmap-ros"
check_pkg "tf2-tools"
set -e

if [ ${#MISSING[@]} -gt 0 ]; then
    echo ""
    fail "缺失包，请手动安装："
    echo -e "  ${BOLD}sudo apt install -y ${MISSING[*]}${NC}"
    exit 1
fi

# 串口
SERIAL=""
for dev in /dev/ttyUSB0 /dev/ttyACM0 /dev/serial/by-id/usb-*; do
    if [ -e "$dev" ]; then
        SERIAL="$dev"
        ok "串口: $SERIAL"
        break
    fi
done
[ -z "$SERIAL" ] && warn "未找到 STM32 串口（启动时自动搜索）"

# D435
if lsusb 2>/dev/null | grep -qi "intel.*realsense"; then
    ok "Intel RealSense 相机"
else
    warn "未检测到 D435 相机"
fi

# ============================================================
# 2. 文件检查（V2 精简版：只需要 SLAM + 探索脚本）
# ============================================================
header "文件验证"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PKG_DIR="$(dirname "$SCRIPT_DIR")"

check_file() {
    if [ -f "$PKG_DIR/$1" ]; then
        ok "$1"
    else
        fail "$1 缺失!"
        exit 1
    fi
}

check_file "scripts/simple_explorer.py"
check_file "launch/stm32_auto_v2.launch"
check_file "launch/d435i_rtabmap.launch"
check_file "scripts/stm32_serial_bridge.py"

if command -v xmllint &>/dev/null; then
    xmllint --noout "$PKG_DIR/launch/stm32_auto_v2.launch" && ok "launch XML 合法"
fi

if [ "$MODE" = "check" ]; then
    header "检查通过 ✅"
    echo ""
    echo "  V2 架构（无需 move_base/explore_lite）："
    echo "  ┌─ ROS: RTAB-Map SLAM + simple_explorer.py（往哪儿走）"
    echo "  └─ STM32: 电机驱动 + 红外/超声波避障安全层"
    echo ""
    echo "  ./stm32_auto_test.sh          # 全自主探索"
    echo "  ./stm32_auto_test.sh keyboard # 手动建图"
    echo ""
    exit 0
fi

# ============================================================
# 3. 编译
# ============================================================
header "编译"

# 自动检测 catkin 工作区路径（相对于脚本位置）
CATKIN_WS="$(cd "$SCRIPT_DIR/../../.." && pwd)"
if [ -d "$CATKIN_WS" ]; then
    source "$CATKIN_WS/devel/setup.bash" 2>/dev/null || true
    (cd "$CATKIN_WS" && catkin_make) || warn "编译有警告"
else
    warn "未找到 catkin_ws"
fi

# ============================================================
# 4. 启动
# ============================================================
echo ""
echo -e "${BOLD}${GRN}══════════════════════════════════════════${NC}"
echo -e "${BOLD}${GRN}  分工会作模式：STM32 负责避障安全         ${NC}"
echo -e "${BOLD}${GRN}  请确认小车放在地面空旷处                 ${NC}"
echo -e "${BOLD}${GRN}══════════════════════════════════════════${NC}"
echo ""

for i in 3 2 1; do
    echo -ne "${YLW}  ⏳ ${i} 秒后启动... (Ctrl+C 取消)${NC}\r"
    sleep 1
done
echo -e "\n"

case "$MODE" in
    explore)
        header "🚀 全自主探索 V2"
        info "simple_explorer.py 读取 RTAB-Map 前沿 → 发 /cmd_vel"
        info "STM32 红外+超声波底层避障，ROS 只管往哪儿走"
        echo ""
        roslaunch orbbec_gemini_slam stm32_auto_v2.launch
        ;;
    keyboard)
        header "🚀 手动遥控建图"
        info "W/S: 前进/后退  A/D: 左转/右转  Q/E: 原地旋  空格: 停"
        echo ""
        roslaunch orbbec_gemini_slam stm32_slam.launch
        ;;
    *)
        fail "未知模式: $MODE"
        echo "  可用: explore | check | keyboard"
        exit 1
        ;;
esac
