# STM32-SLAM-Robot SLAM 移植到 Intel NX — 完整指南

## 📦 本文件夹内容

```
ZYSTM32-SLAM-移植包/
├── STM32固件/          ← 小车 STM32 固件（已修改+编译烧录脚本）
│   ├── USER/           main.c, Makefile, 链接脚本, 烧录脚本
│   ├── SYSTEM/         电机/串口/延时/超声波/舵机/巡线等驱动
│   ├── CORE/           startup_stm32f10x_hd.s (GNU语法)
│   └── STM32F10x_FWLib/ STM32标准外设库 v3.5
├── ROS脚本/            ← ROS 串口桥接 + 键盘遥控 + SLAM launch
├── Tools/              ← 快速测试工具（串口/电机）
└── Docs/               ← 操作指南 + 烧录流程 + 任务存档
```


## ⚠️ 新设备前置依赖（必须先安装）

```bash
# 1. ROS Noetic
sudo apt install ros-noetic-desktop-full

# 2. RealSense SDK + ROS 驱动
sudo apt install ros-noetic-realsense2-camera ros-noetic-realsense2-description

# 3. RTAB-Map
sudo apt install ros-noetic-rtabmap ros-noetic-rtabmap-launch ros-noetic-rtabmap-viz ros-noetic-rtabmap-rviz-plugins

# 4. STM32 交叉编译工具链
sudo apt install gcc-arm-none-eabi binutils-arm-none-eabi

# 5. STM32 串口烧录工具
sudo apt install stm32flash

# 6. Python 依赖（ROS自带了pyserial，但确认一下）
pip3 install pyserial
```

**验证安装：**
```bash
which arm-none-eabi-gcc    # → 必须存在
which stm32flash           # → 必须存在
stm32flash --version       # → 0.5+
which roscore              # → /opt/ros/noetic/bin/roscore
dpkg -l | grep rtabmap-viz # → ros-noetic-rtabmap-viz
```


## 🔧 步骤 1：编译 + 烧录 STM32 固件

```bash
cd STM32固件/USER

# 首次编译
make clean && make

# 免跳线帽一键烧录（CH340 RTS/DTR 自动控制 bootloader）
make flash

# ⚠️ 如果自动烧录失败，手动跳线帽：
#    断USB → BOOT0接VCC → 插USB → RESET → make flash
#    烧完 → BOOT0恢复GND → RESET
```


## 🚀 步骤 2：启动 SLAM 建图

```bash
# 创建 catkin workspace（首次）
mkdir -p ~/catkin_ws/src
cd ~/catkin_ws/src
# 把 ROS脚本 里的 .py 和 .launch 放到一个 package 里
# 或直接用 rosrun 直接跑（无需编译）

# 启动 ROS Master
roscore &

# 启动 SLAM（一条命令启动全部）
source setup_orbbec_slam.sh
roslaunch stm32_slam.launch

# 没有 launch 文件的话，可以逐个启动：
# 终端1: roscore
# 终端2: rosrun your_pkg stm32_serial_bridge.py
# 终端3: roslaunch realsense2_camera rs_camera.launch align_depth:=true
# 终端4: roslaunch rtabmap_launch rtabmap.launch rgb_topic:=/camera/color/image_raw depth_topic:=/camera/aligned_depth_to_color/image_raw camera_info_topic:=/camera/color/camera_info
# 终端5: rosrun your_pkg keyboard_teleop.py
```


## ✅ 步骤 3：快速测试

```bash
# 串口回显（H命令应返回帮助菜单）
python3 test_stm32.py

# 电机直连测试（需电池供电）
python3 test_motor.py

# ROS 单步测试
rostopic pub --once /cmd_vel geometry_msgs/Twist '{linear: {x: 0.2}, angular: {z: 0.0}}'
```


## 🗺️ 地图存储

| 位置 | 说明 |
|------|------|
| `~/.ros/rtabmap.db` | 默认存储位置（ESC/Ctrl+C 自动保存） |
| 查看 | `rtabmap-databaseViewer ~/.ros/rtabmap.db` |
| 导出3D | `rtabmap-export --cloud ~/.ros/rtabmap.db --output map.ply` |
| 导出2D | `rtabmap-export --grid ~/.ros/rtabmap.db` |


## 🐛 已修复的关键 Bug（移植时注意）

| Bug | 文件 | 修复内容 |
|-----|------|---------|
| 链接脚本 FLASH/RAM 不匹配 | stm32f103ve_flash.ld | 512K→256K, 64K→48K (STM32F103VC) |
| GCC printf 无输出 | usart.c | 添加 `_write()` 函数 |
| STM32 DTR 被复位 | 所有 Python 脚本 | `ser.dtr=False; ser.rts=False` |
| 电机停止时方向不定 | motor.c | SetMotorSpeed cSpeed==0 加 else 分支 |
| 后退命令不发 | main.c | 解析前 `buf[len]=0` 空终止 |
| 后退速度映射错误 | main.c | B 命令 `speed=100-speed` |
| 串口缓冲溢出 | stm32_serial_bridge.py | 10Hz + 每次清输出缓冲 |
| 原地旋转太快 | keyboard_teleop.py | Q/E 从 0.8→0.4 rad/s |


## 🔌 硬件连接清单

| 设备 | 接口 | 注意 |
|------|------|------|
| D435 深度相机 | USB 3.0 蓝色口 | **必须 3.0！2.0 无画面** |
| STM32 小车 | 任意 USB | CH340 串口 |
| 小车电池 | 12V 电池组 | 必须打开开关，USB 不够供电电机 |


## 💬 给新 Reasonix Chat 的启动命令

把这个文件路径告诉 Reasonix，然后说：

```
我正在把 STM32-SLAM-Robot SLAM 项目移植到新的 Intel NX 设备上。
请先读取 ~/桌面/ZYSTM32-SLAM-移植包/Docs/STM32-ROS-测试命令.txt
了解完整操作流程，然后帮我检查环境依赖是否安装完毕。
```


## 📋 完整操作命令（在新设备上按顺序执行）

```bash
# 1. 验证硬件
lsusb | grep 8086       # D435 是否在 Bus 002 (USB3.0)
ls /dev/ttyUSB*          # STM32 CH340 是否在线

# 2. 编译烧录固件
cd ~/桌面/ZYSTM32-SLAM-移植包/STM32固件/USER
make clean && make && make flash

# 3. 测试串口
python3 ~/桌面/ZYSTM32-SLAM-移植包/Tools/test_stm32.py

# 4. 测试电机（电池要开）
python3 ~/桌面/ZYSTM32-SLAM-移植包/Tools/test_motor.py

# 5. 启动 ROS + SLAM
roscore &
source ~/桌面/ZYSTM32-SLAM-移植包/ROS脚本/setup_orbbec_slam.sh
roslaunch ~/桌面/ZYSTM32-SLAM-移植包/ROS脚本/stm32_slam.launch

# 6. 键盘遥控建图（WASD 方向，空格停止，ESC 退出）
# （launch 已自动启动键盘遥控）
```
