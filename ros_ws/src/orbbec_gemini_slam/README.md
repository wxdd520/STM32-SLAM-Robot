# Orbbec Gemini 335L + RTAB-Map 双目 SLAM 快速启动

本方案让你的 **奥比中光 Gemini 335L** 双目相机配合 **RTAB-Map** 实现完整的双目 SLAM。

---

## 系统要求

- Ubuntu 20.04 + ROS Noetic ✅（你的环境已满足）
- Orbbec Gemini 335L 通过 USB 连接 ✅
- 棋盘格标定板（用于双目标定，详见第 4 步）

---

## 快速三步走

### 第 1 步：安装依赖

```bash
# 1. 确保 ROS Noetic 环境
source /opt/ros/noetic/setup.bash

# 2. 安装 RTAB-Map 及相关包
sudo apt install ros-noetic-rtabmap-ros \
                 ros-noetic-camera-calibration \
                 ros-noetic-image-pipeline \
                 python3-pip usbutils

# 3. 安装 Python 依赖
pip3 install opencv-python numpy pyyaml
```

### 第 2 步：创建 ROS 工作区并编译

```bash
# 进入本仓库的目录（假设你已经在本 repo 根目录）
cd /path/to/your/repo

# 创建 catkin 工作区
mkdir -p ~/catkin_ws/src
cd ~/catkin_ws

# 将 orbbec_gemini_slam 包链接到工作区
ln -s /path/to/your/repo/orbbec_gemini_slam src/

# 编译
catkin_make
source devel/setup.bash
```

### 第 3 步：测试相机流

先确认相机设备节点：

```bash
ls /dev/video*
```

应该看到类似 `video0 video1 video2 video3 video4` 等多个设备。

运行测试节点查看相机图像：

```bash
roslaunch orbbec_gemini_slam gemini_stereo_only.launch
```

这会打开 OpenCV 窗口显示左右目画面。如果有图像，相机工作正常！

### 第 4 步：双目相机标定（重要，第一次使用时必需）

RTAB-Map 需要准确的相机内参和外参（左右目之间的变换矩阵）。

打印并准备一个棋盘格标定板（建议 9×6 内角点，格子大小 ~25mm）。

新开终端，运行标定：

```bash
# 启动相机
roslaunch orbbec_gemini_slam gemini_stereo_only.launch

# 新终端，启动立体标定（调整棋盘格尺寸）
rosrun camera_calibration cameracalibrator.py \
    --approximate 0.1 \
    --size 9x6 \
    --square 0.025 \
    right:=/gemini/right/image_raw \
    left:=/gemini/left/image_raw \
    right_camera:=/gemini/right \
    left_camera:=/gemini/left
```

- 左右移动棋盘格，直到 CALIBRATE 按钮亮起
- 点击 CALIBRATE → 等待计算
- 点击 SAVE 保存校准结果到 `/tmp/calibrationdata.tar.gz`
- 解压并将 `left.yaml` 和 `right.yaml` 复制到 `config/` 目录

**或者**使用我们提供的快速标定脚本：

```bash
rosrun orbbec_gemini_slam calibrate_stereo.py \
    --left /dev/video1 --right /dev/video2 \
    --rows 9 --cols 6 --square 0.025
```

### 第 5 步：启动 RTAB-Map SLAM！

```bash
# 确保已标定（否则用默认参数会不准）
roslaunch orbbec_gemini_slam gemini_rtabmap.launch
```

这会启动：
1. Gemini 335L 相机节点（发布左右目图像）
2. RTAB-Map 双目里程计
3. RTAB-Map SLAM 核心节点
4. RTAB-Map 可视化界面
5. RViz 可视化

---

## 文件结构

```
orbbec_gemini_slam/
├── README.md                    # 本文件
├── scripts/
│   ├── orbbec_stereo_node.py    # 双目相机 ROS 节点
│   └── calibrate_stereo.py      # 立体标定辅助脚本
├── launch/
│   ├── gemini_stereo_only.launch # 只启动相机（测试用）
│   └── gemini_rtabmap.launch    # 启动相机 + RTAB-Map SLAM
└── config/
    ├── gemini_left.yaml          # 左目相机参数（标定后替换）
    └── gemini_right.yaml         # 右目相机参数（标定后替换）
```

## Gemini 335L 设备号对应关系（典型）

| 设备 | 用途 |
|------|------|
| /dev/video0 (或 video4) | RGB 彩色相机 |
| /dev/video1 (或 video5) | 左目红外相机 |
| /dev/video2 (或 video6) | 右目红外相机 |
| /dev/video3 | 深度图 |

> 具体索引可能因系统而异，运行 `roslaunch orbbec_gemini_slam gemini_stereo_only.launch` 查看 OpenCV 窗口标题即可确认。

## 常见问题

**Q: 画面卡顿/延迟大？**
A: 降低分辨率：修改 launch 文件中的 `WIDTH=640, HEIGHT=480`

**Q: 标定结果不理想？**
A: 确保棋盘格在不同位置、角度、距离都采集了图像，建议至少 20 张有效样本

**Q: 想使用 RGB 图像而非红外？**
A: Gemini 335L 的 RGB 和红外双目是独立的传感器，红外适合低光，RGB 适合白天。修改 node 中的设备索引即可切换
