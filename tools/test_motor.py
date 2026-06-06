#!/usr/bin/env python3
"""ZYSTM32 电机直连测试 — 绕过ROS，直接控制电机"""
import serial, time, glob, os

def find_port():
    for p in glob.glob("/dev/serial/by-id/usb-*") + glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*"):
        if os.path.exists(p): return p
    return None

port = find_port()
if not port:
    print("❌ 未检测到串口！")
    exit(1)
print(f"串口: {port}")

ser = serial.Serial(port, 115200, timeout=0.5)
ser.dtr = False   # 关键：防止复位 STM32
ser.rts = False
time.sleep(0.5)

# 清缓冲
ser.reset_input_buffer()
ser.reset_output_buffer()

def cmd(c):
    ser.write((c + "\r\n").encode())
    ser.flush()
    time.sleep(0.15)
    # 读取回复
    r = b""
    while ser.in_waiting:
        r += ser.read(ser.in_waiting)
        time.sleep(0.03)
    return r.decode(errors='replace').strip()

print("\n=== 测试 H 命令 ===")
print(cmd("H")[:200])

print("\n=== 前进 2 秒 ===")
cmd("F 50")
time.sleep(2)

print("=== 停止 ===")
cmd("S")

print("\n=== 后退 2 秒 ===")
cmd("B 50")
time.sleep(2)

print("=== 停止 ===")
cmd("S")

print("\n=== 左转 1 秒 ===")
cmd("L 50")
time.sleep(1)

print("=== 停止 ===")
cmd("S")

print("\n✅ 测试完成")
ser.close()
