#!/bin/bash
# STM32-SLAM-Robot 串口测试 — 清缓冲 + 发送命令 + 读取回复
set -euo pipefail

find_port() {
    for p in /dev/serial/by-id/usb-* /dev/ttyUSB0 /dev/ttyUSB1 /dev/ttyACM0 /dev/ttyACM1; do
        [ -e "$p" ] && { echo "$p"; return 0; }
    done
    return 1
}

echo "=== 检测串口 ==="
PORT=$(find_port) && echo "在线: $PORT" || { echo "未检测到设备！"; exit 1; }

echo ""
echo "=== 清空缓冲区 (丢弃开机垃圾数据) ==="
stty -F "$PORT" 115200 cs8 -cstopb -parenb raw 2>/dev/null
timeout 0.5 cat "$PORT" 2>/dev/null > /dev/null || true
echo "  完成"

echo ""
echo "=== 发送 H 命令 (第1次) ==="
echo -e "H\r\n" > "$PORT"
sleep 0.3

echo "=== 读取回复 ==="
timeout 0.8 cat "$PORT" 2>/dev/null || true

echo ""
echo "=== 发送 H 命令 (第2次) ==="
echo -e "H\r\n" > "$PORT"
sleep 0.3

echo "=== 读取回复 ==="
timeout 0.8 cat "$PORT" 2>/dev/null || true

echo ""
echo "--- 测试结束 ---"
