#!/usr/bin/env python3
"""
Orbbec Gemini 335L Stereo ROS Node
===================================
通过 UVC 接口捕获奥比中光 Gemini 335L 的双目图像并发布为 ROS 话题。

用法:
  rosrun orbbec_gemini_slam orbbec_stereo_node.py \
    left:=/dev/video1 right:=/dev/video2

话题:
  /gemini/left/image_raw   — 左目图像 (sensor_msgs/Image)
  /gemini/right/image_raw  — 右目图像 (sensor_msgs/Image)
  /gemini/left/camera_info  — 左目相机参数 (sensor_msgs/CameraInfo)
  /gemini/right/camera_info — 右目相机参数 (sensor_msgs/CameraInfo)
"""

import rospy
import cv2
import numpy as np
from sensor_msgs.msg import Image, CameraInfo
from cv_bridge import CvBridge
import sys
import os

class GeminiStereoNode:
    def __init__(self):
        rospy.init_node('gemini_stereo_node', anonymous=False)

        # ========== 参数 ==========
        self.left_dev = rospy.get_param('~left_dev', '/dev/video1')
        self.right_dev = rospy.get_param('~right_dev', '/dev/video2')
        self.width = rospy.get_param('~width', 640)
        self.height = rospy.get_param('~height', 400)
        self.fps = rospy.get_param('~fps', 30)
        self.frame_id = rospy.get_param('~frame_id', 'gemini_optical_frame')
        self.camera_name = rospy.get_param('~camera_name', 'gemini')

        # 是否使用 OpenNI2 后端 (某些 Orbbec 相机需要)
        self.use_openni = rospy.get_param('~use_openni', False)

        # ========== 相机校准文件路径 ==========
        self.left_calib_file = rospy.get_param(
            '~left_calib', 
            os.path.join(os.path.dirname(__file__), '..', 'config', 'gemini_left.yaml')
        )
        self.right_calib_file = rospy.get_param(
            '~right_calib',
            os.path.join(os.path.dirname(__file__), '..', 'config', 'gemini_right.yaml')
        )

        # ========== 发布器 ==========
        self.left_pub = rospy.Publisher('~left/image_raw', Image, queue_size=5)
        self.right_pub = rospy.Publisher('~right/image_raw', Image, queue_size=5)
        self.left_info_pub = rospy.Publisher('~left/camera_info', CameraInfo, queue_size=5)
        self.right_info_pub = rospy.Publisher('~right/camera_info', CameraInfo, queue_size=5)

        self.bridge = CvBridge()

        # ========== 打开摄像头 ==========
        self.left_cap = None
        self.right_cap = None
        self._open_cameras()

        # ========== 加载或生成校准信息 ==========
        self.left_cam_info = self._load_camera_info(self.left_calib_file, 'left')
        self.right_cam_info = self._load_camera_info(self.right_calib_file, 'right')

        rospy.loginfo(f"✅ Gemini 335L 节点已启动")
        rospy.loginfo(f"   左目: {self.left_dev} -> /gemini/left/image_raw")
        rospy.loginfo(f"   右目: {self.right_dev} -> /gemini/right/image_raw")
        rospy.loginfo(f"   分辨率: {self.width}x{self.height} @ {self.fps}fps")

    def _open_cameras(self):
        """打开左右目摄像头"""
        # 尝试多种后端
        backends = [cv2.CAP_V4L2, cv2.CAP_ANY]
        
        for backend in backends:
            if backend == cv2.CAP_V4L2:
                rospy.loginfo(f"尝试 V4L2 后端打开 {self.left_dev}...")
            else:
                rospy.loginfo(f"尝试默认后端打开 {self.left_dev}...")

            self.left_cap = cv2.VideoCapture(self.left_dev, backend)
            if self.left_cap.isOpened():
                break
            self.left_cap.release()
            self.left_cap = None

        if self.left_cap is None:
            rospy.logerr(f"❌ 无法打开左目相机 {self.left_dev}")
            rospy.logerr("请检查设备节点是否存在: ls /dev/video*")
            sys.exit(1)

        # 右目
        for backend in backends:
            if backend == cv2.CAP_V4L2:
                rospy.loginfo(f"尝试 V4L2 后端打开 {self.right_dev}...")
            else:
                rospy.loginfo(f"尝试默认后端打开 {self.right_dev}...")

            self.right_cap = cv2.VideoCapture(self.right_dev, backend)
            if self.right_cap.isOpened():
                break
            self.right_cap.release()
            self.right_cap = None

        if self.right_cap is None:
            rospy.logerr(f"❌ 无法打开右目相机 {self.right_dev}")
            sys.exit(1)

        # 设置分辨率 & FPS
        for cap, name in [(self.left_cap, 'left'), (self.right_cap, 'right')]:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            cap.set(cv2.CAP_PROP_FPS, self.fps)
            
            actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            rospy.loginfo(f"   {name} 实际分辨率: {actual_w}x{actual_h}")

    def _load_camera_info(self, yaml_path, side):
        """
        从 YAML 文件加载 CameraInfo，如果文件不存在则返回默认参数。
        """
        ci = CameraInfo()
        ci.header.frame_id = self.frame_id
        ci.width = self.width
        ci.height = self.height

        if os.path.exists(yaml_path):
            try:
                import yaml
                with open(yaml_path, 'r') as f:
                    data = yaml.safe_load(f)

                # ROS camera_calibration 输出的格式
                if 'camera_matrix' in data:
                    K = data['camera_matrix']['data']
                    D = data['distortion_coefficients']['data']
                    R = data.get('rectification_matrix', {}).get('data', [1,0,0,0,1,0,0,0,1])
                    P = data.get('projection_matrix', {}).get('data', [])
                else:
                    # 嵌套格式
                    K = data.get('K', [])
                    D = data.get('D', [])
                    R = data.get('R', [1,0,0,0,1,0,0,0,1])
                    P = data.get('P', [])

                if len(K) >= 9:
                    ci.K = K
                if len(D) > 0:
                    ci.D = D
                if len(R) >= 9:
                    ci.R = R
                if len(P) >= 12:
                    ci.P = P
                ci.distortion_model = data.get('distortion_model', 'plumb_bob')

                rospy.loginfo(f"✅ 已加载 {side} 目校准文件: {yaml_path}")
            except Exception as e:
                rospy.logwarn(f"⚠️ 读取校准文件失败: {e}，使用默认参数")
                self._set_default_camera_info(ci)
        else:
            rospy.logwarn(f"⚠️ 未找到 {side} 目校准文件: {yaml_path}")
            rospy.logwarn(f"   使用默认参数（约 640x480, FX=FY=500, CX=320, CY=240）")
            rospy.logwarn(f"   请先标定相机以获得准确结果！")
            self._set_default_camera_info(ci)

        return ci

    def _set_default_camera_info(self, ci):
        """设置默认的 CameraInfo（640x480 假设）"""
        fx = 500.0  # 典型值，实际值需标定
        fy = 500.0
        cx = self.width / 2.0
        cy = self.height / 2.0
        ci.K = [fx, 0, cx, 0, fy, cy, 0, 0, 1]
        ci.D = [0, 0, 0, 0, 0]
        ci.R = [1, 0, 0, 0, 1, 0, 0, 0, 1]
        ci.P = [fx, 0, cx, 0, 0, fy, cy, 0, 0, 0, 1, 0]
        ci.distortion_model = 'plumb_bob'

    def _auto_white_balance(self, left_frame, right_frame):
        """简单的自动白平衡（对红外图做直方图均衡）"""
        if len(left_frame.shape) == 2:  # 灰度图
            left_eq = cv2.equalizeHist(left_frame)
            right_eq = cv2.equalizeHist(right_frame)
            return left_eq, right_eq
        return left_frame, right_frame

    def run(self):
        """主循环：捕获并发布图像"""
        rate = rospy.Rate(self.fps)
        seq = 0

        while not rospy.is_shutdown():
            ret_l, left_frame = self.left_cap.read()
            ret_r, right_frame = self.right_cap.read()

            if not ret_l or not ret_r:
                rospy.logwarn_throttle(2.0, "读取图像失败，重试中...")
                rate.sleep()
                continue

            # 如果相机输出 BGR 彩色，转为灰度（双目 SLAM 通常用灰度）
            if len(left_frame.shape) == 3:
                left_frame = cv2.cvtColor(left_frame, cv2.COLOR_BGR2GRAY)
            if len(right_frame.shape) == 3:
                right_frame = cv2.cvtColor(right_frame, cv2.COLOR_BGR2GRAY)

            # 可选：直方图均衡（改善纹理弱环境下的匹配）
            if rospy.get_param('~equalize', False):
                left_frame, right_frame = self._auto_white_balance(left_frame, right_frame)

            now = rospy.Time.now()

            # 生成 ROS Image 消息
            left_msg = self.bridge.cv2_to_imgmsg(left_frame, encoding='mono8')
            left_msg.header.stamp = now
            left_msg.header.seq = seq
            left_msg.header.frame_id = self.frame_id

            right_msg = self.bridge.cv2_to_imgmsg(right_frame, encoding='mono8')
            right_msg.header.stamp = now
            right_msg.header.seq = seq
            right_msg.header.frame_id = self.frame_id

            # CameraInfo
            self.left_cam_info.header.stamp = now
            self.left_cam_info.header.seq = seq
            self.right_cam_info.header.stamp = now
            self.right_cam_info.header.seq = seq

            # 发布
            self.left_pub.publish(left_msg)
            self.right_pub.publish(right_msg)
            self.left_info_pub.publish(self.left_cam_info)
            self.right_info_pub.publish(self.right_cam_info)

            # 按频率控制
            rate.sleep()
            seq += 1

        # 清理
        self.left_cap.release()
        self.right_cap.release()
        rospy.loginfo("相机已关闭")


if __name__ == '__main__':
    try:
        node = GeminiStereoNode()
        node.run()
    except rospy.ROSInterruptException:
        pass
    except Exception as e:
        rospy.logerr(f"异常: {e}")
        import traceback
        traceback.print_exc()
