#!/usr/bin/env python3
"""
Orbbec Gemini 335L 快速测试脚本
在宿主机上运行，验证左右目相机都能正常出图。
用法:
  python3 test_gemini.py
  python3 test_gemini.py --device /dev/video1  # 指定设备
"""

import cv2
import argparse
import os
import sys

def find_gemini_devices():
    """扫描 /dev/video* 找到 Gemini 摄像头的设备"""
    gemini_devices = []
    for i in range(10):
        path = f"/dev/video{i}"
        if os.path.exists(path):
            cap = cv2.VideoCapture(path, cv2.CAP_V4L2)
            if cap.isOpened():
                # 读取一帧测试
                ret, frame = cap.read()
                if ret:
                    h, w = frame.shape[:2] if len(frame.shape) == 3 else (frame.shape[0], frame.shape[1])
                    gemini_devices.append((path, w, h))
                cap.release()
    return gemini_devices

def test_single_camera(device_path):
    """测试一个视频设备"""
    cap = cv2.VideoCapture(device_path, cv2.CAP_V4L2)
    if not cap.isOpened():
        print(f"❌ 无法打开 {device_path}")
        return False
    
    # 尝试不同的分辨率
    for w, h in [(640, 480), (1280, 720), (320, 240)]:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
        ret, frame = cap.read()
        if ret:
            actual_h, actual_w = frame.shape[:2] if len(frame.shape) == 3 else (frame.shape[0], frame.shape[1])
            print(f"  ✅ {w}x{h} -> 实际 {actual_w}x{actual_h}")
        else:
            print(f"  ❌ {w}x{h} -> 无图像")
    
    cap.release()

def live_view(left_dev, right_dev):
    """实时显示左右目图像"""
    cap_l = cv2.VideoCapture(left_dev, cv2.CAP_V4L2)
    cap_r = cv2.VideoCapture(right_dev, cv2.CAP_V4L2)
    
    if not cap_l.isOpened():
        print(f"❌ 无法打开左目: {left_dev}")
        return
    if not cap_r.isOpened():
        print(f"❌ 无法打开右目: {right_dev}")
        return
    
    # 设置分辨率
    for cap in [cap_l, cap_r]:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    print(f"\n📷 按 ESC 退出实时预览")
    print(f"   左目: {left_dev}  右目: {right_dev}")
    
    while True:
        ret_l, frame_l = cap_l.read()
        ret_r, frame_r = cap_r.read()
        
        if not ret_l or not ret_r:
            print("⚠️ 读取失败")
            break
        
        # 如果彩色转灰度
        if len(frame_l.shape) == 3:
            gray_l = cv2.cvtColor(frame_l, cv2.COLOR_BGR2GRAY)
        else:
            gray_l = frame_l
        if len(frame_r.shape) == 3:
            gray_r = cv2.cvtColor(frame_r, cv2.COLOR_BGR2GRAY)
        else:
            gray_r = frame_r
        
        # 拼接显示
        h, w = gray_l.shape
        display = cv2.hconcat([gray_l, gray_r])
        display_color = cv2.cvtColor(display, cv2.COLOR_GRAY2BGR)
        
        # 在中间画一条分割线
        cv2.line(display_color, (w, 0), (w, h), (0, 255, 0), 2)
        cv2.putText(display_color, "LEFT", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(display_color, "RIGHT", (w + 10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        cv2.imshow(f"Orbbec Gemini 335L - {left_dev} | {right_dev}", display_color)
        
        key = cv2.waitKey(10) & 0xFF
        if key == 27:  # ESC
            break
    
    cap_l.release()
    cap_r.release()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Gemini 335L 快速测试')
    parser.add_argument('--left', default=None, help='左目设备（不指定则自动扫描）')
    parser.add_argument('--right', default=None, help='右目设备（不指定则自动扫描）')
    parser.add_argument('--scan', action='store_true', help='只扫描不显示')
    parser.add_argument('--test', action='store_true', help='测试分辨率')
    args = parser.parse_args()
    
    if args.left and args.right:
        left_dev, right_dev = args.left, args.right
    else:
        print("🔍 扫描 Gemini 摄像头设备...")
        found = []
        for i in range(10):
            path = f"/dev/video{i}"
            if os.path.exists(path):
                try:
                    # 通过名称判断
                    name_path = f"/sys/class/video4linux/video{i}/name"
                    if os.path.exists(name_path):
                        name = open(name_path).read().strip()
                    else:
                        name = "unknown"
                    
                    cap = cv2.VideoCapture(path, cv2.CAP_V4L2)
                    if cap.isOpened():
                        ret, frame = cap.read()
                        if ret:
                            h, w = frame.shape[:2] if len(frame.shape) == 3 else (frame.shape[0], frame.shape[1])
                            found.append((i, path, name, w, h))
                        cap.release()
                except:
                    pass
        
        print(f"\n找到 {len(found)} 个可用视频设备:")
        gemini_devices = []
        for idx, path, name, w, h in found:
            is_gemini = "Gemini" in name or "Orbbec" in name
            tag = " 🎯 Gemini" if is_gemini else ""
            if is_gemini:
                gemini_devices.append((idx, path))
            print(f"  video{idx}: {path}  {name}  ({w}x{h}){tag}")
        
        if not gemini_devices:
            print("\n❌ 未找到 Gemini 摄像头。请检查:")
            print("   1. 相机 USB 是否已连接")
            print("   2. 是否有权限访问: sudo chmod 666 /dev/video*")
            sys.exit(1)
        
        # 自动选择左右目（UVC 双目的设备号通常是连续的）
        gemini_devices.sort()
        left_dev = gemini_devices[0][1]
        right_dev = gemini_devices[1][1] if len(gemini_devices) > 1 else gemini_devices[0][1]
        print(f"\n自动选择: 左目={left_dev}, 右目={right_dev}")
    
    if args.scan:
        sys.exit(0)
    
    if args.test:
        print(f"\n测试左目 {left_dev}:")
        test_single_camera(left_dev)
        print(f"\n测试右目 {right_dev}:")
        test_single_camera(right_dev)
        sys.exit(0)
    
    # 默认：实时预览
    live_view(left_dev, right_dev)
