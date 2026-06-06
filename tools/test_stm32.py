#!/usr/bin/env python3
"""STM32-SLAM-Robot 串口测试 — 单次打开连接，发送命令，读取回复"""
import serial, time, glob, os

def find_port():
    for p in glob.glob("/dev/serial/by-id/usb-*") + glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*"):
        if os.path.exists(p): return p
    return None

port = find_port()
if not port:
    print("未检测到串口！")
    exit(1)
print(f"串口: {port}")

# 关键：打开时关闭 DTR/RTS，防止复位 STM32
ser = serial.Serial(port, 115200, timeout=0.5)
ser.dtr = False   # 不要拉低 DTR（否则复位 STM32）  
ser.rts = False

# 清缓冲（丢弃开机消息）
time.sleep(0.3)
ser.reset_input_buffer()
ser.reset_output_buffer()

# 发送 H 命令
ser.write(b"H\r\n")
ser.flush()
time.sleep(0.3)

# 读取回复
data = b""
while ser.in_waiting:
    data += ser.read(ser.in_waiting)
    time.sleep(0.05)

print(f"\n回复 ({len(data)} 字节):")
print(data.decode('utf-8', errors='replace'))

ser.close()
