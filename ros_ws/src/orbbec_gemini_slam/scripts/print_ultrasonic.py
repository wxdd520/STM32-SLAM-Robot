#!/usr/bin/env python3
"""
打印超声波距离（调试用）
订阅 /ultrasonic_distance 话题并格式化输出
"""

import rospy
from std_msgs.msg import UInt16


def callback(msg):
    dist = msg.data
    if dist > 0:
        bar_len = min(40, dist // 10)
        bar = '█' * bar_len
        rospy.loginfo(f"超声波: {dist:4d}mm  |{bar}")
    else:
        rospy.logwarn("超声波: 超出量程或无回波")


def main():
    rospy.init_node('ultrasonic_printer')
    rospy.Subscriber('/ultrasonic_distance', UInt16, callback, queue_size=10)
    rospy.loginfo("超声波距离监控已启动 (topic: /ultrasonic_distance)")
    rospy.spin()


if __name__ == '__main__':
    try:
        main()
    except rospy.ROSInterruptException:
        pass
