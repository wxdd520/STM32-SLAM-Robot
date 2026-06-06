#!/usr/bin/env python3
"""
Orbbec Gemini 335L 立体标定辅助脚本
====================================
使用棋盘格对双目相机进行标定，生成 CameraInfo 的 YAML 文件。

用法:
  python3 calibrate_stereo.py --left /dev/video1 --right /dev/video2

依赖:
  pip3 install opencv-python numpy pyyaml
"""

import cv2
import numpy as np
import argparse
import os
import sys
import yaml

def parse_args():
    parser = argparse.ArgumentParser(description='Gemini 335L 双目标定')
    parser.add_argument('--left', default='/dev/video1', help='左目视频设备')
    parser.add_argument('--right', default='/dev/video2', help='右目视频设备')
    parser.add_argument('--rows', type=int, default=9, help='棋盘格内角点行数')
    parser.add_argument('--cols', type=int, default=6, help='棋盘格内角点列数')
    parser.add_argument('--square', type=float, default=0.025, help='棋盘格边长（米）')
    parser.add_argument('--width', type=int, default=640, help='采集宽度')
    parser.add_argument('--height', type=int, default=480, help='采集高度')
    parser.add_argument('--out', default='.', help='输出目录（默认当前目录）')
    return parser.parse_args()


def calibrate_stereo(args):
    # 棋盘格规格
    board_size = (args.cols, args.rows)  # (内角列, 内角行)
    square_size = args.square

    # 准备世界坐标系中的棋盘格角点坐标
    objp = np.zeros((board_size[0] * board_size[1], 3), np.float32)
    objp[:, :2] = np.mgrid[0:board_size[0], 0:board_size[1]].T.reshape(-1, 2)
    objp *= square_size

    # 存储标定数据
    obj_points = []  # 世界坐标系点
    img_points_l = []  # 左目图像点
    img_points_r = []  # 右目图像点

    # 打开摄像头
    cap_l = cv2.VideoCapture(args.left, cv2.CAP_V4L2)
    cap_r = cv2.VideoCapture(args.right, cv2.CAP_V4L2)

    if not cap_l.isOpened():
        print(f"❌ 无法打开左目相机: {args.left}")
        return False
    if not cap_r.isOpened():
        print(f"❌ 无法打开右目相机: {args.right}")
        return False

    for cap in [cap_l, cap_r]:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)

    print(f"📷 打开相机: 左={args.left} 右={args.right}")
    print(f"🎯 棋盘格: {board_size[0]}x{board_size[1]} 内角点, 边长 {square_size*1000:.1f}mm")
    print(f"📝 按键说明:")
    print(f"   空格/Space — 采集当前帧")
    print(f"   C         — 开始标定并保存")
    print(f"   ESC/Q     — 退出")
    print(f"   已采集: 0 对")

    # 标定终止条件
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

    frame_count = 0
    calibrating = False

    while True:
        ret_l, frame_l = cap_l.read()
        ret_r, frame_r = cap_r.read()

        if not ret_l or not ret_r:
            print("⚠️ 读取帧失败，重试...")
            continue

        # 转灰度
        gray_l = cv2.cvtColor(frame_l, cv2.COLOR_BGR2GRAY) if len(frame_l.shape) == 3 else frame_l
        gray_r = cv2.cvtColor(frame_r, cv2.COLOR_BGR2GRAY) if len(frame_r.shape) == 3 else frame_r

        # 查找棋盘格角点
        found_l, corners_l = cv2.findChessboardCorners(gray_l, board_size, None)
        found_r, corners_r = cv2.findChessboardCorners(gray_r, board_size, None)

        # 绘制角点
        display_l = cv2.cvtColor(gray_l, cv2.COLOR_GRAY2BGR)
        display_r = cv2.cvtColor(gray_r, cv2.COLOR_GRAY2BGR)

        if found_l:
            cv2.drawChessboardCorners(display_l, board_size, corners_l, found_l)
        if found_r:
            cv2.drawChessboardCorners(display_r, board_size, corners_r, found_r)

        # 拼接显示
        h, w = gray_l.shape
        display = np.hstack((display_l, display_r))
        cv2.putText(display, f"Captured: {frame_count}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        if found_l and found_r:
            cv2.putText(display, "BOTH FOUND - press SPACE", (w + 10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        else:
            cv2.putText(display, "Move chessboard!", (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        cv2.imshow('Stereo Calibration (left | right)', display)
        key = cv2.waitKey(10) & 0xFF

        if key == 27 or key == ord('q') or key == ord('Q'):
            # ESC/Q — 退出
            break
        elif key == ord(' ') and found_l and found_r:
            # 空格 — 采集
            corners_l_refined = cv2.cornerSubPix(gray_l, corners_l, (11, 11), (-1, -1), criteria)
            corners_r_refined = cv2.cornerSubPix(gray_r, corners_r, (11, 11), (-1, -1), criteria)

            obj_points.append(objp)
            img_points_l.append(corners_l_refined)
            img_points_r.append(corners_r_refined)
            frame_count += 1
            print(f"✅ 采集第 {frame_count} 对")
        elif key == ord('c') or key == ord('C'):
            # C — 标定
            if frame_count < 10:
                print(f"⚠️ 样本太少 ({frame_count})，建议至少 15-20 对")
                continue
            calibrating = True
            break

    cap_l.release()
    cap_r.release()
    cv2.destroyAllWindows()

    if (not calibrating) or frame_count < 3:
        print("❌ 标定取消或样本不足")
        return False

    print(f"\n🔧 开始标定（{frame_count} 对样本）...")

    # ========== 单目标定 ==========
    print("   左目标定中...")
    ret_l, mtx_l, dist_l, rvecs_l, tvecs_l = cv2.calibrateCamera(
        obj_points, img_points_l, gray_l.shape[::-1], None, None)
    print(f"   左目重投影误差: {ret_l:.4f}")

    print("   右目标定中...")
    ret_r, mtx_r, dist_r, rvecs_r, tvecs_r = cv2.calibrateCamera(
        obj_points, img_points_r, gray_r.shape[::-1], None, None)
    print(f"   右目重投影误差: {ret_r:.4f}")

    # ========== 双目标定 ==========
    print("   立体标定中...")
    flags = cv2.CALIB_FIX_INTRINSIC
    ret_s, mtx_l, dist_l, mtx_r, dist_r, R, T, E, F = cv2.stereoCalibrate(
        obj_points, img_points_l, img_points_r,
        mtx_l, dist_l, mtx_r, dist_r,
        gray_l.shape[::-1], criteria=criteria, flags=flags)
    print(f"   立体重投影误差: {ret_s:.4f}")

    # ========== 立体校正 ==========
    print("   计算校正映射...")
    R1, R2, P1, P2, Q, valid_roi1, valid_roi2 = cv2.stereoRectify(
        mtx_l, dist_l, mtx_r, dist_r,
        gray_l.shape[::-1], R, T,
        alpha=0, newImageSize=(w, h))

    # ========== 保存结果 ==========
    def make_camera_yaml(mtx, dist, R, P, width, height, name):
        """生成 ROS camera_calibration 格式的 YAML"""
        data = {
            'image_width': width,
            'image_height': height,
            'camera_name': name,
            'camera_matrix': {
                'rows': 3, 'cols': 3,
                'data': mtx.flatten().tolist()
            },
            'distortion_model': 'plumb_bob',
            'distortion_coefficients': {
                'rows': 1, 'cols': 5,
                'data': dist.flatten().tolist() if len(dist.shape) > 1 else dist.tolist()
            },
            'rectification_matrix': {
                'rows': 3, 'cols': 3,
                'data': R.flatten().tolist()
            },
            'projection_matrix': {
                'rows': 3, 'cols': 4,
                'data': P.flatten().tolist()
            },
        }
        return data

    left_yaml = make_camera_yaml(mtx_l, dist_l, R1, P1, w, h, 'gemini_left')
    right_yaml = make_camera_yaml(mtx_r, dist_r, R2, P2, w, h, 'gemini_right')

    # 也保存系统的变换矩阵（R, T, Q）
    stereo_yaml = {
        'stereo': {
            'R': R.flatten().tolist(),
            'T': T.flatten().tolist(),
            'Q': Q.flatten().tolist(),
            'baseline': float(-T[0][0]) if T.shape == (3, 1) else float(-T[0]),
        }
    }

    out_dir = args.out
    os.makedirs(out_dir, exist_ok=True)

    left_path = os.path.join(out_dir, 'gemini_left.yaml')
    right_path = os.path.join(out_dir, 'gemini_right.yaml')
    stereo_path = os.path.join(out_dir, 'gemini_stereo.yaml')

    for path, data in [(left_path, left_yaml), (right_path, right_yaml), (stereo_path, stereo_yaml)]:
        with open(path, 'w') as f:
            yaml.dump(data, f, default_flow_style=None, sort_keys=False)
        print(f"💾 已保存: {path}")

    print(f"\n🎉 标定完成！")
    print(f"   基线距离: {float(-T[0][0]) if T.shape == (3, 1) else float(-T[0]):.4f} m")
    print(f"\n将生成的 gemini_left.yaml 和 gemini_right.yaml 复制到:")
    print(f"   cp {left_path} ../config/")
    print(f"   cp {right_path} ../config/")

    # 显示校正效果
    print("\n按任意键关闭校正效果预览...")
    cap_l = cv2.VideoCapture(args.left, cv2.CAP_V4L2)
    cap_r = cv2.VideoCapture(args.right, cv2.CAP_V4L2)
    for cap in [cap_l, cap_r]:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)

    # 计算校正映射表
    map1_l, map2_l = cv2.initUndistortRectifyMap(mtx_l, dist_l, R1, P1, (w, h), cv2.CV_32FC1)
    map1_r, map2_r = cv2.initUndistortRectifyMap(mtx_r, dist_r, R2, P2, (w, h), cv2.CV_32FC1)

    for _ in range(100):  # 预览 100 帧
        ret_l, frame_l = cap_l.read()
        ret_r, frame_r = cap_r.read()
        if not ret_l or not ret_r:
            break

        gray_l = cv2.cvtColor(frame_l, cv2.COLOR_BGR2GRAY) if len(frame_l.shape) == 3 else frame_l
        gray_r = cv2.cvtColor(frame_r, cv2.COLOR_BGR2GRAY) if len(frame_r.shape) == 3 else frame_r

        rect_l = cv2.remap(gray_l, map1_l, map2_l, cv2.INTER_LINEAR)
        rect_r = cv2.remap(gray_r, map1_r, map2_r, cv2.INTER_LINEAR)

        # 画水平线以检查校正效果
        vis = np.hstack((rect_l, rect_r))
        vis_color = cv2.cvtColor(vis, cv2.COLOR_GRAY2BGR)
        for y in range(0, h, 30):
            cv2.line(vis_color, (0, y), (w * 2, y), (0, 255, 0), 1)

        cv2.imshow('Rectified (press any key to exit)', vis_color)
        if cv2.waitKey(10) != -1:
            break

    cap_l.release()
    cap_r.release()
    cv2.destroyAllWindows()
    return True


if __name__ == '__main__':
    args = parse_args()
    success = calibrate_stereo(args)
    sys.exit(0 if success else 1)
