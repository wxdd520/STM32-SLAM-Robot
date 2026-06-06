#!/usr/bin/env python3
"""
键盘遥控 - STM32-SLAM-Robot SLAM
按住即走，松开即停，30Hz 持续发送命令
"""

import sys, select, tty, termios
import rospy
from geometry_msgs.msg import Twist

BIND = {
    'w': ( 0.2,  0.0, 'F'),
    's': (-0.2,  0.0, 'B'),
    'a': ( 0.0,  0.5, 'L'),
    'd': ( 0.0, -0.5, 'R'),
    'q': ( 0.0,  0.4, 'SL'),    # 原地旋速度减半
    'e': ( 0.0, -0.4, 'SR'),
    ' ': ( 0.0,  0.0, 'S'),
}

class KeyboardTeleop:
    def __init__(self):
        rospy.init_node('keyboard_teleop')
        self.pub = rospy.Publisher('/cmd_vel', Twist, queue_size=1)
        self.speed_mult = 1.0
        self.running = True
        self.active_key = None

        print("\n========================================")
        print("  STM32-SLAM-Robot 键盘遥控")
        print("========================================")
        print("  W/S   前进/后退")
        print("  A/D   左转/右转")
        print("  Q/E   原地左旋/右旋")
        print("  空格  停止")
        print("  +/-   速度倍率")
        print("  ESC   退出")
        print("========================================")

    def run(self):
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        new = termios.tcgetattr(fd)
        new[3] &= ~(termios.ICANON | termios.ECHO)
        new[6][termios.VMIN] = 0
        new[6][termios.VTIME] = 0
        termios.tcsetattr(fd, termios.TCSADRAIN, new)

        try:
            self._loop()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
            self._publish(0, 0)
            print("\n🛑 已退出")

    def _publish(self, linear, angular):
        twist = Twist()
        twist.linear.x = linear
        twist.angular.z = angular
        self.pub.publish(twist)

    def _loop(self):
        rate = rospy.Rate(30)  # 30Hz 持续发布
        last_print = ''

        while self.running and not rospy.is_shutdown():
            # 非阻塞读取按键
            while True:
                r, _, _ = select.select([sys.stdin], [], [], 0)
                if not r:
                    break
                ch = sys.stdin.read(1)
                if not ch:
                    break
                if ch == '\x1b':
                    self.running = False
                    return
                if ch == '+':
                    self.speed_mult = min(3.0, self.speed_mult + 0.2)
                    print(f"  🔼 x{self.speed_mult:.1f}")
                    continue
                if ch == '-':
                    self.speed_mult = max(0.2, self.speed_mult - 0.2)
                    print(f"  🔽 x{self.speed_mult:.1f}")
                    continue
                self.active_key = ch

            # 根据当前按下的键发布速度
            if self.active_key and self.active_key in BIND:
                l, a, tag = BIND[self.active_key]
                self._publish(l * self.speed_mult, a * self.speed_mult)
                current = tag
            else:
                self._publish(0, 0)
                current = 'S'

            if current != last_print:
                print(f"  {'⏹ STOP' if current == 'S' else f'▶ {current:2s} x{self.speed_mult:.1f}'}")
                last_print = current

            rate.sleep()


if __name__ == '__main__':
    try:
        KeyboardTeleop().run()
    except rospy.ROSInterruptException:
        pass
