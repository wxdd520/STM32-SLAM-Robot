#!/bin/bash
# =============================================================
#  ZYSTM32-A1 运行脚本（统一入口）
#  用法: bash scripts/run.sh [模式]
#
#  模式:
#    (无参数)       交互式菜单
#    serial         串口直连测试 (screen)
#    bridge         启动 ROS 串口桥接
#    teleop         串口桥接 + rostopic 指令测试
#    slam           SLAM 建图 + 自动开键盘遥控
#    auto           全自主探索 V2 + 自动开键盘遥控
#    explore        全自主探索 V1 (explore_lite)
#    nav            导航模式 (已有地图)
#    test           快速功能验证
#    flash          编译并烧录固件
#    env            仅 source 环境（用法: source scripts/run.sh env）
# =============================================================

set +e  # 交互式脚本不要 set -e

# 自动检测项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
FIRMWARE_DIR="$PROJECT_DIR/firmware/USER"

# ── 颜色 ──────────────────────────────────────────────
RED='\033[0;31m'; GRN='\033[0;32m'; YLW='\033[1;33m'
CYN='\033[0;36m'; NC='\033[0m'; BOLD='\033[1m'

info()  { echo -e "${CYN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GRN}[ OK ]${NC}  $*"; }
warn()  { echo -e "${YLW}[WARN]${NC}  $*"; }
fail()  { echo -e "${RED}[FAIL]${NC} $*"; }

# ── 环境初始化 ────────────────────────────────────────
setup_env() {
    if [ -f /opt/ros/noetic/setup.bash ]; then
        source /opt/ros/noetic/setup.bash
    else
        echo -e "${RED}[ERROR]${NC} ROS Noetic 未安装"; return 1
    fi
    if [ -f "$PROJECT_DIR/ros_ws/devel/setup.bash" ]; then
        source "$PROJECT_DIR/ros_ws/devel/setup.bash"
    else
        echo -e "${YLW}[WARN]${NC} catkin 工作区未编译，先运行: bash install.sh"
        return 1
    fi
}

# ── 串口自动检测 ──────────────────────────────────────
find_serial() {
    for dev in /dev/serial/by-id/usb-* /dev/ttyUSB* /dev/ttyACM*; do
        [ -e "$dev" ] && echo "$dev" && return 0
    done
    echo ""
    return 1
}

# ── 确保 roscore 运行 ────────────────────────────────
ensure_roscore() {
    if ! pgrep -x roscore > /dev/null 2>&1; then
        echo -e "${CYN}▶ 启动 roscore...${NC}"
        roscore &
        sleep 3
    fi
}

# ── 自动开新终端运行节点 ─────────────────────────────
# 用法: open_new_terminal "节点说明" rosrun参数...
open_new_terminal() {
    local label="$1"; shift
    local cmd="cd '$PROJECT_DIR' && source scripts/setup_env.sh && $*"

    for term in gnome-terminal xterm xfce4-terminal konsole mate-terminal lxterminal; do
        if command -v "$term" &>/dev/null; then
            case "$term" in
                gnome-terminal)
                    gnome-terminal -- bash -c "$cmd; exec bash" &
                    echo -e "${GRN}✅ 已在新终端打开: $label${NC}"
                    sleep 2
                    return 0 ;;
                xfce4-terminal)
                    xfce4-terminal --hold -e "bash -c '$cmd'" &
                    echo -e "${GRN}✅ 已在新终端打开: $label${NC}"
                    sleep 2
                    return 0 ;;
                konsole)
                    konsole --hold -e bash -c "$cmd" &
                    echo -e "${GRN}✅ 已在新终端打开: $label${NC}"
                    sleep 2
                    return 0 ;;
                *)
                    "$term" -e "bash -c '$cmd'" &
                    echo -e "${GRN}✅ 已在新终端打开: $label${NC}"
                    sleep 2
                    return 0 ;;
            esac
        fi
    done

    echo -e "${YLW}⚠ 未找到终端模拟器，请另开终端执行:${NC}"
    echo -e "   cd $PROJECT_DIR && source scripts/setup_env.sh"
    echo -e "   $*"
    echo ""
    return 1
}

# ── 交互式菜单 ────────────────────────────────────────
show_menu() {
    echo ""
    echo -e "${BOLD}${CYN}╔══════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${CYN}║         ZYSTM32-A1 运行菜单                      ║${NC}"
    echo -e "${BOLD}${CYN}╠══════════════════════════════════════════════════╣${NC}"
    echo -e "${BOLD}${CYN}║                                                  ║${NC}"
    echo -e "${BOLD}${CYN}║  ${GRN}1${CYN}  串口直连测试    (screen)              ${CYN}║${NC}"
    echo -e "${BOLD}${CYN}║  ${GRN}2${CYN}  ROS 串口桥接    (bridge only)         ${CYN}║${NC}"
    echo -e "${BOLD}${CYN}║  ${GRN}3${CYN}  ROS 指令测试    (bridge + rostopic)   ${CYN}║${NC}"
    echo -e "${BOLD}${CYN}║  ${GRN}4${CYN}  SLAM 建图       (D435 + 遥控)        ${CYN}║${NC}"
    echo -e "${BOLD}${CYN}║  ${GRN}5${CYN}  全自主探索 V2   (SLAM + 探索)        ${CYN}║${NC}"
    echo -e "${BOLD}${CYN}║  ${GRN}6${CYN}  全自主探索 V1   (explore_lite)       ${CYN}║${NC}"
    echo -e "${BOLD}${CYN}║  ${GRN}7${CYN}  导航模式        (已有地图)            ${CYN}║${NC}"
    echo -e "${BOLD}${CYN}║  ${GRN}8${CYN}  快速功能验证                            ${CYN}║${NC}"
    echo -e "${BOLD}${CYN}║  ${GRN}9${CYN}  编译并烧录固件                          ${CYN}║${NC}"
    echo -e "${BOLD}${CYN}║  ${GRN}0${CYN}  退出                                    ${CYN}║${NC}"
    echo -e "${BOLD}${CYN}║                                                  ║${NC}"
    echo -e "${BOLD}${CYN}╚══════════════════════════════════════════════════╝${NC}"
    echo ""
    read -p "  选择 [0-9]: " choice
    case "$choice" in
        1) mode_serial ;;
        2) mode_bridge ;;
        3) mode_teleop ;;
        4) mode_slam ;;
        5) mode_auto_v2 ;;
        6) mode_explore_v1 ;;
        7) mode_nav ;;
        8) mode_test ;;
        9) mode_flash ;;
        0) echo "再见！"; exit 0 ;;
        *) echo "无效选项"; show_menu ;;
    esac
}

# ── 模式实现 ──────────────────────────────────────────

mode_serial() {
    local port
    port=$(find_serial)
    if [ -z "$port" ]; then
        echo -e "${RED}[ERROR]${NC} 未检测到串口，请确认 USB 已连接"
        return 1
    fi
    echo -e "${CYN}串口: $port${NC}"
    echo -e "${YLW}进入 screen (敲 H 回车看帮助, Ctrl+A K 退出)${NC}"
    screen "$port" 115200
}

mode_bridge() {
    setup_env
    ensure_roscore
    local port
    port=$(find_serial)
    echo -e "${CYN}串口: ${port:-auto}${NC}"
    rosrun orbbec_gemini_slam stm32_serial_bridge.py _port:="${port:-auto}"
}

mode_teleop() {
    setup_env
    ensure_roscore
    local port
    port=$(find_serial)

    echo -e "${CYN}启动 ROS 串口桥接...${NC}"
    rosrun orbbec_gemini_slam stm32_serial_bridge.py _port:="${port:-auto}" &
    BRIDGE_PID=$!
    sleep 2

    echo ""
    echo -e "${GRN}桥接已启动！${NC}"
    echo "rostopic pub /cmd_vel 指令示例："
    echo ""
    echo "  # 前进"
    echo "  rostopic pub /cmd_vel geometry_msgs/Twist '{linear: {x: 0.3}}' -r 3"
    echo ""
    echo "  # 停车"
    echo "  rostopic pub /cmd_vel geometry_msgs/Twist '{linear: {x: 0}}' -1"
    echo ""
    echo "  # 左转"
    echo "  rostopic pub /cmd_vel geometry_msgs/Twist '{angular: {z: 0.6}}' -r 3"
    echo ""
    echo -e "${YLW}按 Ctrl+C 停止桥接${NC}"
    wait $BRIDGE_PID 2>/dev/null || true
}

mode_slam() {
    setup_env
    ensure_roscore
    echo -e "${GRN}启动 SLAM 建图...${NC}"
    open_new_terminal "键盘遥控 (WASDQE)" "rosrun orbbec_gemini_slam keyboard_teleop.py"
    roslaunch orbbec_gemini_slam zystm32_slam.launch keyboard:=false
}

mode_auto_v2() {
    setup_env
    ensure_roscore
    echo -e "${GRN}启动全自主探索 V2 (SLAM + simple_explorer)...${NC}"
    open_new_terminal "键盘遥控 (WASDQE)" "rosrun orbbec_gemini_slam keyboard_teleop.py"
    roslaunch orbbec_gemini_slam zystm32_auto_v2.launch keyboard:=false
}

mode_explore_v1() {
    setup_env
    ensure_roscore
    echo -e "${GRN}启动全自主探索 V1 (explore_lite + move_base)...${NC}"
    roslaunch orbbec_gemini_slam zystm32_auto_explore.launch
}

mode_nav() {
    setup_env
    ensure_roscore
    echo -e "${GRN}启动导航模式...${NC}"
    roslaunch orbbec_gemini_slam zystm32_nav.launch
}

mode_test() {
    setup_env
    echo ""
    echo -e "${BOLD}${CYN}════ ZYSTM32-A1 快速功能验证 ════${NC}"
    echo ""

    echo -e "${CYN}[1/5] ROS 环境${NC}"
    echo "  ROS_DISTRO=$ROS_DISTRO"
    echo "  ROS_PACKAGE_PATH=$(echo $ROS_PACKAGE_PATH | tr ':' '\n' | head -3)"
    ok "ROS 环境正常"
    echo ""

    echo -e "${CYN}[2/5] ROS 功能包${NC}"
    for pkg in orbbec_gemini_slam rtabmap_ros realsense2_camera move_base explore_lite; do
        rospack find "$pkg" &>/dev/null && ok "$pkg" || echo -e "  ${RED}✗ $pkg${NC}"
    done
    echo ""

    echo -e "${CYN}[3/5] 串口设备${NC}"
    local port
    port=$(find_serial)
    if [ -n "$port" ]; then ok "串口: $port"
    else echo -e "  ${YLW}⚠ 未检测到串口（插入 STM32 USB 后重试）${NC}"; fi
    echo ""

    echo -e "${CYN}[4/5] Launch 文件${NC}"
    local launch_dir="$PROJECT_DIR/ros_ws/src/orbbec_gemini_slam/launch"
    for f in zystm32_slam.launch zystm32_auto_v2.launch d435i_rtabmap.launch zystm32_nav.launch; do
        [ -f "$launch_dir/$f" ] && ok "$f" || echo -e "  ${RED}✗ $f${NC}"
    done
    echo ""

    echo -e "${CYN}[5/5] STM32 固件${NC}"
    [ -f "$FIRMWARE_DIR/zystm32_a1_slam.bin" ] && ok "zystm32_a1_slam.bin" || echo -e "  ${YLW}⚠ 未编译 (cd firmware/USER && make)${NC}"

    echo ""
    echo -e "${BOLD}${GRN}════ 验证完成 ════${NC}"
}

mode_flash() {
    if command -v arm-none-eabi-gcc &>/dev/null; then
        info "编译固件..."
        cd "$FIRMWARE_DIR"
        make clean && make all
        echo ""
        info "烧录中..."
        make flash
    else
        echo -e "${RED}[ERROR]${NC} arm-none-eabi-gcc 未安装"
        echo "  安装: sudo apt install gcc-arm-none-eabi binutils-arm-none-eabi"
    fi
}

# ── 主入口 ────────────────────────────────────────────
MODE="${1:-menu}"

case "$MODE" in
    serial)    mode_serial ;;
    bridge)    mode_bridge ;;
    teleop)    mode_teleop ;;
    slam)      mode_slam ;;
    auto)      mode_auto_v2 ;;
    explore)   mode_explore_v1 ;;
    nav)       mode_nav ;;
    test)      setup_env; mode_test ;;
    flash)     mode_flash ;;
    env)       setup_env ;;
    menu|*)    show_menu ;;
esac
