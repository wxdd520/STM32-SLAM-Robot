#!/bin/bash
###############################################################################
# STM32 Flash Script — STM32-SLAM-Robot
# 自动检测串口、验证 bootloader 模式、烧录固件，带详细报错和调试信息
###############################################################################

set -euo pipefail

# ── 配置 ──────────────────────────────────────────────────────
BIN_FILE="./stm32_slam_robot.bin"
HEX_FILE="./stm32_slam_robot.hex"
BAUD=115200
FLASH_ADDR=0x08000000
RED='\033[0;31m'
GRN='\033[0;32m'
YEL='\033[1;33m'
BLD='\033[1m'
RST='\033[0m'

msg()  { echo -e "${BLD}[*]${RST} $*"; }
ok()   { echo -e "${GRN}${BLD}[✓]${RST} $*"; }
warn() { echo -e "${YEL}${BLD}[!]${RST} $*"; }
err()  { echo -e "${RED}${BLD}[✗]${RST} $*"; }
die()  { err "$*"; echo; exit 1; }

# ── 1. 检测串口 ────────────────────────────────────────────────
msg "步骤 1: 检测串口设备..."

# 优先 /dev/serial/by-id，其次 ttyUSB，最后 ttyACM
PORT=""
for candidate in \
    /dev/serial/by-id/usb-* \
    /dev/ttyUSB0 /dev/ttyUSB1 /dev/ttyUSB2 /dev/ttyUSB3 \
    /dev/ttyACM0 /dev/ttyACM1 /dev/ttyACM2 /dev/ttyACM3; do
    if [ -e "$candidate" ]; then
        PORT="$candidate"
        break
    fi
done

if [ -z "$PORT" ]; then
    echo
    err "未检测到任何串口设备！"
    echo
    echo "  请确认："
    echo "    1. USB 线已连接 STM32 板"
    echo "    2. STM32 板已上电（LED 亮起）"
    echo "    3. 用 lsusb 检查 CH340 设备是否存在"
    echo
    echo "  lsusb 输出:"
    lsusb 2>/dev/null | grep -i -E "ch34|stm|usb.serial" || echo "    (未找到 CH340/STM32 设备)"
    echo
    echo "  dmesg 最近 5 行:"
    dmesg | tail -5 | sed 's/^/    /'
    echo
    die "请确保小车 USB 已连接且上电，然后重试。"
fi
ok "检测到串口: ${PORT}"

# ── 2. 检查串口是否被占用 ──────────────────────────────────────
msg "步骤 2: 检查串口是否被占用..."

OCCUPIED=$(fuser "${PORT}" 2>/dev/null || true)
if [ -n "$OCCUPIED" ]; then
    warn "串口 ${PORT} 被以下进程占用 (PID: ${OCCUPIED})"
    ps -p "$OCCUPIED" -o pid,comm,args 2>/dev/null || true
    echo
    echo -n "  是否杀掉占用进程? [y/N] "
    read -r REPLY
    if [[ "$REPLY" =~ ^[Yy]$ ]]; then
        fuser -k "${PORT}" 2>/dev/null || true
        sleep 1
        ok "已释放串口"
    else
        die "请手动释放串口后重试。"
    fi
else
    ok "串口空闲"
fi

# ── 3. 探测 STM32 bootloader ───────────────────────────────────
msg "步骤 3: 探测 STM32 bootloader..."

PROBE_OUTPUT=$(stm32flash "${PORT}" 2>&1) || {
    echo
    err "STM32 bootloader 探测失败！"
    echo
    echo "  原始输出:"
    echo "    ${PROBE_OUTPUT}" | sed 's/^/    /'
    echo
    echo "  可能原因和解决步骤："
    echo
    echo "  ┌────────────────────────────────────────────────┐"
    echo "  │  $(
        if echo "$PROBE_OUTPUT" | grep -qi "failed to init\|no response\|timeout\|0x"; then
            echo "⇢ STM32 未进入系统 bootloader 模式"
        elif echo "$PROBE_OUTPUT" | grep -qi "permission"; then
            echo "⇢ 权限不足，试试 sudo"
        else
            echo "⇢ 无法与 STM32 bootloader 通信"
        fi
    ) │"
    echo "  └────────────────────────────────────────────────┘"
    echo
    echo "  请严格按以下顺序操作，然后重新运行本脚本："
    echo
    echo "    ${BLD}1)${RST} 断开 USB 线"
    echo "    ${BLD}2)${RST} BOOT0 跳线帽 → ${YEL}VCC${RST} (3.3V)"
    echo "    ${BLD}3)${RST} BOOT1 跳线帽 → ${YEL}GND${RST} (如有)"
    echo "    ${BLD}4)${RST} 插上 USB 线 (此时板子自动上电)"
    echo "    ${BLD}5)${RST} 按一下板上的 ${YEL}RESET${RST} 键"
    echo "    ${BLD}6)${RST} 重新运行: ${YEL}$0${RST}"
    echo
    echo "  debug技巧：用串口助手连 ${PORT} (115200 8E1)，发 0x7F,"
    echo "          STM32 bootloader 应回复 0x79。未回复说明没进 bootloader。"
    echo
    exit 1
}

# 提取芯片信息
CHIP_INFO=$(echo "$PROBE_OUTPUT" | grep -i -E "Device|Version|PID|Flash|RAM|Family" | head -10 || true)
ok "STM32 bootloader 已响应！"
if [ -n "$CHIP_INFO" ]; then
    echo "$CHIP_INFO" | sed 's/^/      /'
fi

# ── 4. 选择固件格式并烧录 ──────────────────────────────────────
msg "步骤 4: 烧录固件..."

FIRMWARE_TYPE="bin"

if [ ! -f "$BIN_FILE" ]; then
    warn ".bin 文件不存在 ($BIN_FILE)，尝试 .hex..."
    FIRMWARE_TYPE="hex"
    if [ ! -f "$HEX_FILE" ]; then
        die ".hex 文件也不存在 ($HEX_FILE)！请先执行 make 编译。"
    fi
fi

FILE="${BIN_FILE}"
[ "$FIRMWARE_TYPE" = "hex" ] && FILE="${HEX_FILE}"

echo "      固件: ${FILE} ($(stat --format='%s' "$FILE") bytes)"
echo "      串口: ${PORT}"

echo
FLASH_OUTPUT=$(
    stm32flash -w "${FILE}" -v -g "${FLASH_ADDR}" "${PORT}" 2>&1
) || {
    echo
    err "烧录失败！"
    echo
    echo "  输出:"
    echo "${FLASH_OUTPUT}" | sed 's/^/    /'
    echo

    # 尝试给针对性建议
    if echo "$FLASH_OUTPUT" | grep -qi "write protect\|protection\|locked"; then
        echo "  建议: 芯片被写保护，尝试解锁："
        echo "    stm32flash -k ${PORT}              # 解除读保护（会擦除芯片！）"
        echo "    stm32flash -u ${PORT}              # 解除写保护"
    elif echo "$FLASH_OUTPUT" | grep -qi "timeout"; then
        echo "  建议: 通信超时，降低波特率试试："
        echo "    stm32flash -b 57600 -w ${FILE} -v -g ${FLASH_ADDR} ${PORT}"
    elif echo "$FLASH_OUTPUT" | grep -qi "verify\|mismatch"; then
        echo "  建议: 校验失败（写入后读回不一致），降低波特率或检查硬件连接。"
    else
        echo "  建议: 重新进入 bootloader 模式再试（断 USB → BOOT0=VCC → 插USB → RESET）"
    fi
    echo
    exit 1
}

ok "烧录 + 验证 成功！"
echo

# ── 5. 显示结果摘要 ────────────────────────────────────────────
msg "固件信息:"
SIZE_TEXT=$(arm-none-eabi-size stm32_slam_robot.elf 2>/dev/null | tail -1 || echo "N/A")
echo "      ${SIZE_TEXT}"

echo
echo "  ┌─────────────────────────────────────────────┐"
echo "  │             ✅  烧录完成！                  │"
echo "  └─────────────────────────────────────────────┘"
echo
echo "  后续操作:"
echo "    1) 断开 USB 线"
echo "    2) BOOT0 跳线帽恢复为 ${YEL}GND${RST}"
echo "    3) 重新插上 USB"
echo "    4) 按 RESET 重启（或重新上电）"
echo
echo "  测试: 串口助手连 ${PORT} (115200 8N1), 发送 ${YEL}H 回车${RST}"
echo
