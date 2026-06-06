#!/usr/bin/env python3
"""
STM32-SLAM-Robot 一键烧录（免拨跳线帽）
通过 CH340 的 RTS/DTR 自动控制 STM32 进入/退出 bootloader
"""

import serial
import subprocess
import sys
import time
import os
import glob

# ── 配置 ──────────────────────────────────────────────
BIN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stm32_slam_robot.bin")
FLASH_ADDR = "0x08000000"
STM32FLASH_BIN = "/usr/bin/stm32flash"

# ── 查找串口 ──────────────────────────────────────────
def find_port():
    candidates = (glob.glob("/dev/serial/by-id/usb-*")
                + glob.glob("/dev/ttyUSB*")
                + glob.glob("/dev/ttyACM*"))
    for c in candidates:
        if os.path.exists(c):
            return c
    return None

# ── 通过 RTS/DTR 进入 bootloader ──────────────────────
def enter_bootloader(port_name):
    """RTS→BOOT0, DTR→RESET (典型 CH340 接线)"""
    print(f"[*] 通过 RTS/DTR 控制 STM32 进入 bootloader ...")
    ser = serial.Serial(port_name, 115200, timeout=0.5)

    # 阶段1: DTR=0 (复位), RTS=1 (BOOT0=1 进bootloader)
    ser.dtr = False
    ser.rts = True
    time.sleep(0.15)

    # 阶段2: DTR=1 (释放复位), RTS=1 (保持BOOT0=1)
    ser.dtr = True
    ser.rts = True
    time.sleep(0.15)

    ser.close()
    print("[✓] 已发送 bootloader 进入信号")
    time.sleep(0.3)  # 等 STM32 bootloader 启动

# ── 退出 bootloader，恢复正常运行 ─────────────────────
def exit_bootloader(port_name):
    """RTS=0 (BOOT0=0), DTR 复位脉冲"""
    ser = serial.Serial(port_name, 115200, timeout=0.5)
    ser.rts = False   # BOOT0=0
    ser.dtr = False   # 复位
    time.sleep(0.05)
    ser.dtr = True    # 释放复位, 正常启动
    time.sleep(0.05)
    ser.close()

# ── 主流程 ─────────────────────────────────────────────
def main():
    print("=" * 55)
    print("  STM32-SLAM-Robot 一键烧录 (免跳线帽)")
    print("=" * 55)
    print()

    # 1. 找串口
    port = find_port()
    if not port:
        print("[✗] 未检测到串口！请确认 USB 已连接。")
        sys.exit(1)
    print(f"[*] 串口: {port}")

    # 2. 检查固件
    if not os.path.exists(BIN_FILE):
        print(f"[✗] 固件不存在: {BIN_FILE}")
        sys.exit(1)
    size = os.path.getsize(BIN_FILE)
    print(f"[*] 固件: {BIN_FILE} ({size} bytes)")

    # 3. 自动进入 bootloader (通过 RTS/DTR)
    try:
        enter_bootloader(port)
    except Exception as e:
        print(f"[✗] 无法控制串口: {e}")
        print()
        print("  备选方案 (手动跳线帽):")
        print("    断USB → BOOT0接VCC → 插USB → RESET → 重试本脚本")
        sys.exit(1)

    # 4. 烧录
    print()
    print("[*] 开始烧录...")
    cmd = [STM32FLASH_BIN, "-w", BIN_FILE, "-v", "-g", FLASH_ADDR, port]
    print(f"    {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr)

    if result.returncode != 0:
        print("[✗] 烧录失败！")
        err = result.stdout + result.stderr
        if "write protect" in err.lower() or "locked" in err.lower():
            print("    芯片写保护，尝试: stm32flash -u " + port)
        elif "timeout" in err.lower():
            print("    RTS/DTR 自动进入 bootloader 可能失败")
            print("    请手动操作: 断USB → BOOT0接VCC(下) → 插USB → RESET → 重试")
        sys.exit(1)

    print("[✓] 烧录+校验成功！")

    # 5. 自动恢复正常运行 (BOOT0=0, 复位)
    try:
        exit_bootloader(port)
        print("[✓] 已自动复位到正常运行模式")
    except Exception:
        print("[!] 自动复位失败，请手动: 断USB → BOOT0拨回GND → 插USB → RESET")

    print()
    print("=" * 55)
    print("  ✅ 全部完成！现在可以测试串口命令。")
    print(f"  screen {port} 115200    → 敲 H 回车")
    print("=" * 55)


if __name__ == "__main__":
    main()
