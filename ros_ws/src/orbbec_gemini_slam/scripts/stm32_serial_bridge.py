#!/usr/bin/env python3
"""
ROS Serial Bridge: /cmd_vel → STM32 Serial (ZySTM32-A1)
流式控制：20Hz 持续发送当前速度命令，无指令自动停。
"""

import rospy
import serial
import time
import threading
import glob
import os
from geometry_msgs.msg import Twist
from std_msgs.msg import UInt16


class STM32SerialBridge:
    def __init__(self):
        rospy.init_node('stm32_serial_bridge', anonymous=True)

        port = rospy.get_param('~port', 'auto')
        if port == 'auto':
            port = self._find_port()
        baud = rospy.get_param('~baud', 115200)
        self.rate_hz = 10           # 降低发送频率避免串口拥塞
        self.cmd_timeout = 1.0     # 1秒无指令才停车（3Hz 发指令间隔 0.33s，留足余量）

        self.lock = threading.Lock()
        self.running = True
        self.cmd = 'S'             # 当前要发送的命令
        self.last_cmd_time = 0.0
        self._last_sent = None     # 上次实际发送的（避免刷屏）

        # 连接串口
        try:
            self.ser = serial.Serial(port, baud, timeout=0.1)
            self.ser.dtr = False
            self.ser.rts = False
            time.sleep(0.3)
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
        except serial.SerialException as e:
            rospy.logerr(f"无法打开串口 {port}: {e}")
            rospy.signal_shutdown("串口连接失败")
            return

        rospy.loginfo(f"✅ {port} @ {baud}bps | {self.rate_hz}Hz 流式控制")

        # 订阅 /cmd_vel
        rospy.Subscriber('/cmd_vel', Twist, self.cmd_vel_callback, queue_size=1)
        self.ultrasonic_pub = rospy.Publisher('/ultrasonic_distance', UInt16, queue_size=10)

        # 发送线程
        self.send_thread = threading.Thread(target=self.send_loop, daemon=True)
        self.send_thread.start()

        # 接收线程
        self.recv_thread = threading.Thread(target=self.recv_loop, daemon=True)
        self.recv_thread.start()

        rospy.loginfo("🚀 流式桥接已启动")

    def _find_port(self):
        for p in (glob.glob('/dev/serial/by-id/usb-*')
                + glob.glob('/dev/ttyUSB*')
                + glob.glob('/dev/ttyACM*')):
            if os.path.exists(p):
                return p
        return '/dev/ttyUSB0'

    def cmd_vel_callback(self, msg):
        """收到 /cmd_vel → 更新要发送的命令"""
        linear = msg.linear.x
        angular = msg.angular.z

        if abs(linear) < 0.02 and abs(angular) < 0.03:
            cmd = 'S'
        else:
            speed = int(abs(linear) / 0.5 * 100)
            speed = min(100, max(30, speed))
            turn = int(abs(angular) / 1.5 * 100)
            turn = min(100, max(40, turn))

            if abs(angular) < 0.05:
                cmd = f'F {speed}' if linear > 0 else f'B {speed}'
            elif abs(linear) < 0.03:
                cmd = f'SL {turn}' if angular > 0 else f'SR {turn}'
            else:
                val = max(speed, turn)
                cmd = f'L {val}' if angular > 0 else f'R {val}'

        with self.lock:
            self.cmd = cmd
            self.last_cmd_time = time.time()

    def _send(self, cmd):
        try:
            self.ser.reset_output_buffer()
            self.ser.write((cmd + '\r\n').encode())
        except serial.SerialException:
            pass

    def send_loop(self):
        """10Hz 持续发送——无指令超时则自动停"""
        rate = rospy.Rate(self.rate_hz)
        while not rospy.is_shutdown() and self.running:
            with self.lock:
                elapsed = time.time() - self.last_cmd_time
                cmd = self.cmd

            # 超时 → 自动停
            if elapsed > self.cmd_timeout:
                cmd = 'S'
                with self.lock:
                    self.cmd = 'S'

            # 每次都发送（流式控制，STM32 需要持续收到命令才知道仍在运动）
            self._send(cmd)

            # 只在命令变化时打印日志
            if cmd != self._last_sent:
                rospy.loginfo(f"▶ {cmd}" if cmd != 'S' else f"⏹ S")
                self._last_sent = cmd

            rate.sleep()

    def recv_loop(self):
        buf = b''
        while not rospy.is_shutdown() and self.running:
            try:
                if self.ser.in_waiting > 0:
                    buf += self.ser.read(self.ser.in_waiting)
                    while b'\r\n' in buf:
                        line, buf = buf.split(b'\r\n', 1)
                        if line:
                            s = line.decode('utf-8', errors='replace').strip()
                            if s.startswith('D '):
                                try:
                                    self.ultrasonic_pub.publish(int(s.split()[1]))
                                except (IndexError, ValueError):
                                    pass
                            elif s and not s.startswith('OK '):
                                rospy.logdebug(f"📨 {s}")
                else:
                    time.sleep(0.01)
            except (serial.SerialException, UnicodeDecodeError):
                time.sleep(0.1)

    def shutdown(self):
        self.running = False
        self._send('S')
        self.ser.close()
        rospy.loginfo("串口桥接已关闭")


if __name__ == '__main__':
    try:
        bridge = STM32SerialBridge()
        rospy.on_shutdown(bridge.shutdown)
        rospy.spin()
    except rospy.ROSInterruptException:
        pass
