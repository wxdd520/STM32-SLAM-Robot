# ZYSTM32-A1: ROS SLAM Robot with STM32 Ultrasonic Avoidance 🤖

> **ZYSTM32-A1 亚克力四驱底盘 + STM32F103VC 超声波避障 + ROS Noetic RTAB-Map SLAM**
>
> 一款低成本、开箱即用的 ROS SLAM 机器人：STM32 负责底层电机驱动与超声波避障，上位机运行 RTAB-Map RGB-D SLAM 实时建图，支持键盘遥控、全自主探索和导航。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Platform](https://img.shields.io/badge/platform-Ubuntu%2020.04-blue)
![ROS](https://img.shields.io/badge/ROS-Noetic-green)
![MCU](https://img.shields.io/badge/MCU-STM32F103VC-orange)

---

## 📋 目录

- [项目概述](#-项目概述)
- [硬件清单](#-硬件清单)
- [系统架构](#-系统架构)
- [快速开始](#-快速开始)
- [固件编译与烧录](#-固件编译与烧录)
- [ROS 工作区](#-ros-工作区)
- [使用指南](#-使用指南)
- [串口协议](#-串口协议)
- [模式切换](#-模式切换)
- [项目文件结构](#-项目文件结构)
- [常见故障排查](#-常见故障排查)
- [已修复 Bug 记录](#-已修复-bug-记录)
- [开发计划](#-开发计划)
- [许可证](#-许可证)

---

## 🎯 项目概述

ZYSTM32-A1 是一个**入门级 ROS SLAM 机器人平台**，旨在用最低成本实现：

- ✅ **超声波自主避障** — 舵机扫描前/左/右三个方向，自动避障前进
- ✅ **ROS 串口遥控** — 通过 `/cmd_vel` 话题控制小车运动
- ✅ **RTAB-Map RGB-D SLAM 建图** — 实时构建 3D 点云和 2D 占据栅格地图
- ✅ **按键模式切换** — AUTO（避障）/ MANUAL（遥控）一键切换
- ✅ **自动回退** — 5 秒无 ROS 指令自动回到避障模式

### 项目背景

本项目基于智宇科技 ZYSTM32-A1 亚克力四驱机器人底盘改造，将原始的单片机例程升级为完整的 ROS + SLAM 系统，实现了从"遥控小车"到"自主建图机器人"的跨越。

---

## 🔧 硬件清单

| 组件 | 型号 | 说明 |
|------|------|------|
| **主控板** | STM32F103VC (Cortex-M3, 72MHz) | 下位机，负责电机控制/传感器/串口通信 |
| **深度相机** | Intel RealSense D435 | RGB-D 相机，用于 RTAB-Map SLAM 建图 |
| **超声波模块** | HC-SR04 × 1 | 测距避障（配合舵机扫描） |
| **舵机** | SG90 / MG995 | 搭载超声波，扫描前/左/右方向 |
| **电机驱动** | L298N / 板载驱动 | 4 路直流电机 |
| **红外传感器** | 循迹/避障红外 × 2 | 辅助避障 |
| **串口芯片** | CH340G | USB 转串口，用于烧录和 ROS 通信 |
| **电池** | 12V 锂电池组 | 给电机和主板供电 |
| **上位机** | Ubuntu 20.04 电脑 | 运行 ROS Noetic + RTAB-Map |

### 硬件连接

```
STM32F103VC
├── USART1 (PA9/PA10) ── CH340 ── USB ── 电脑 (ROS)
├── TIM4 (PB6-PB9)     ── 4路电机 PWM
├── TIM5 (PA0)         ── 舵机 PWM
├── HC-SR04            ── Trig/ECHO GPIO
├── KEY + LED (D3/D4)  ── 按键 + 模式指示
└── 红外避障传感器      ── GPIO 输入

Intel D435 ── USB 3.0 ── 电脑 (ROS)
```

> ⚠️ **D435 必须插 USB 3.0（蓝色）接口**，USB 2.0 无图像数据。

---

## 🏗️ 系统架构

```
┌──────────────────────────────────────────────────────┐
│                    上位机 (电脑)                        │
│  ┌──────────────────────────────────────────────┐   │
│  │  ROS Noetic                                   │   │
│  │  ┌────────────────┐  ┌──────────────────┐   │   │
│  │  │ keyboard_teleop│  │ stm32_serial_    │   │   │
│  │  │ (键盘遥控)      │  │ bridge.py        │   │   │
│  │  └───────┬────────┘  │ (串口桥接)        │   │   │
│  │          │ /cmd_vel  └────────┬─────────┘   │   │
│  │          │                    │ 串口         │   │
│  │  ┌───────┴────────────────────┴──────────┐  │   │
│  │  │  RTAB-Map SLAM                        │  │   │
│  │  │  (RGB-D SLAM + 回环检测 + 全局优化)    │  │   │
│  │  └───────────────────────────────────────┘  │   │
│  │            │ D435 相机数据                   │   │
│  └────────────┼────────────────────────────────┘   │
└───────────────┼────────────────────────────────────┘
                │ 串口 (115200bps, /dev/ttyUSB0)
                ▼
┌──────────────────────────────────────────────────────┐
│                    下位机 (STM32F103VC)                │
│  ┌──────────────────────────────────────────────┐   │
│  │  main.c (主循环)                             │   │
│  │  ├── 串口命令解析 (F/B/L/R/S/SL/SR/G/D/H)   │   │
│  │  ├── 超声波舵机扫描 (前90°/左175°/右5°)      │   │
│  │  ├── AUTO 避障状态机                          │   │
│  │  └── 模式切换 (AUTO/MANUAL)                  │   │
│  └──────────────┬───────────────────────────────┘   │
│                 │                                    │
│  ┌──────────────┴───────────────────────────────┐   │
│  │  SYSTEM 驱动层                                │   │
│  │  motor.c usart.c UltrasonicWave.c             │   │
│  │  Server.c IRAvoid.c keysacn.c delay.c        │   │
│  └──────────────┬───────────────────────────────┘   │
│                 │ GPIO / PWM / TIM                   │
│  ┌──────────────┴───────────────────────────────┐   │
│  │  硬件层                                       │   │
│  │  4×直流电机  超声波HC-SR04   舵机 SG90        │   │
│  │  2×红外传感器  按键   2×LED   CH340串口       │   │
│  └──────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────┘
```

### 数据流

```
键盘输入 (WASD)
    │
    ▼
keyboard_teleop.py ──→ /cmd_vel (geometry_msgs/Twist)
                            │
                            ├──→ stm32_serial_bridge.py ──串口──→ STM32 → 电机
                            │
                            └──→ RTAB-Map (视觉里程计 + 建图)
                                       │
                                       └──→ RViz (可视化)
```

---

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/your-username/ZYSTM32-A1.git
cd ZYSTM32-A1
```

### 2. 一键部署

```bash
bash install.sh
```

`install.sh` 会自动完成：
1. ✅ 检查并安装所有依赖（ROS、工具链、Python包）
2. ✅ 编译 STM32 固件
3. ✅ 编译 ROS catkin 工作区
4. ✅ 验证所有组件

### 3. 烧录固件

```bash
cd firmware/USER && make flash
```

### 4. 运行（三种方式）

```bash
# 方式一：交互式菜单（推荐新手）
bash scripts/run.sh

# 方式二：一键启动 SLAM
bash scripts/start_slam.sh

# 方式三：手动
source scripts/setup_env.sh
roslaunch orbbec_gemini_slam zystm32_slam.launch
```

### `run.sh` 快速命令

```bash
bash scripts/run.sh serial     # 串口直连测试
bash scripts/run.sh bridge     # ROS 串口桥接
bash scripts/run.sh slam       # SLAM 建图 + 键盘遥控
bash scripts/run.sh auto       # 全自主探索
bash scripts/run.sh nav        # 导航模式
bash scripts/run.sh test       # 快速功能验证
bash scripts/run.sh flash      # 编译并烧录固件
```

> 💡 **所有脚本自动检测项目路径，可放在任意目录使用。**

---

## 🔥 固件编译与烧录

### 编译

```bash
cd firmware/USER

make clean && make    # 编译
```

成功的输出会显示固件大小：

```
   text	   data	    bss	    dec	    hex	filename
  16604	    136	   2432	  19172	  4ae4	zystm32_a1_slam.elf
```

生成文件：
- `zystm32_a1_slam.elf` — ELF 格式（调试用）
- `zystm32_a1_slam.bin` — 纯二进制（烧录用）
- `zystm32_a1_slam.hex` — Intel HEX 格式
- `zystm32_a1_slam.map` — 符号映射表

### 一键烧录（推荐）

```bash
make flash
```

`flash_auto.py` 会自动完成：
1. 检测 CH340 串口
2. 通过 RTS/DTR 控制 STM32 进入 bootloader
3. 调用 `stm32flash` 烧录 + 校验
4. 自动复位 STM32 到正常运行模式

### 手动烧录（备用方案）

如果自动烧录失败：

```bash
# 1. 断开 USB
# 2. BOOT0 跳线帽从 GND 改接到 VCC（3.3V）
# 3. 重新插上 USB
# 4. 按一下 RESET 键
# 5. 手动烧录
stm32flash -w zystm32_a1_slam.bin -v -g 0x08000000 /dev/ttyUSB0

# 6. 断 USB，BOOT0 恢复为 GND
# 7. 重新插 USB，按 RESET
```

### 芯片配置

| 参数 | 值 |
|------|-----|
| MCU | STM32F103VC (High Density) |
| Flash | 256KB (0x08000000 - 0x0803FFFF) |
| RAM | 48KB (0x20000000 - 0x2000BFFF) |
| HSE | 8MHz |
| 系统时钟 | 72MHz (PLL 9x) |
| 串口 | 115200bps, 8N1 |
| 工具链 | arm-none-eabi-gcc |

> ⚠️ **注意：芯片型号是 F103VC 而非 F103VE！**
> 原始的链接脚本按 512KB Flash / 64KB RAM 配置，与实际芯片不符。
> 已修正为 256KB Flash / 48KB RAM。

---

## 🤖 ROS 工作区

### 功能包：`orbbec_gemini_slam`

#### 启动文件 (Launch Files)

| 文件 | 用途 |
|------|------|
| `zystm32_slam.launch` | **一键启动** — 串口桥接 + D435 + RTAB-Map + 键盘遥控 |
| `d435i_rtabmap.launch` | D435 + RTAB-Map RGB-D SLAM 核心配置 |
| `d435i_preview.launch` | D435 相机预览（不含 SLAM） |
| `zystm32_auto_explore.launch` | 全自主探索模式（含 explore_lite） |
| `zystm32_nav.launch` | 导航模式（move_base + 路径规划） |
| `gemini_rtabmap.launch` | Orbbec Gemini 335L 双目 SLAM |
| `gemini_stereo_only.launch` | Gemini 双目预览 |

#### 脚本 (Python Nodes)

| 文件 | 用途 |
|------|------|
| `stm32_serial_bridge.py` | ROS `/cmd_vel` → STM32 串口命令，10Hz 流式控制 |
| `keyboard_teleop.py` | 键盘遥控 (WASDQE) |
| `simple_explorer.py` | 简单自主探索节点 |
| `calibrate_stereo.py` | 双目相机标定工具 |
| `orbbec_stereo_node.py` | Gemini 335L 驱动节点 |
| `test_gemini.py` | Gemini 相机测试 |

#### 配置文件

| 文件 | 用途 |
|------|------|
| `config/gemini_rtabmap.rviz` | RViz 预设视图配置 |
| `config/gemini_left.yaml` | Gemini 左目相机标定 |
| `config/gemini_right.yaml` | Gemini 右目相机标定 |
| `config/costmap_common.yaml` | move_base 通用代价地图参数 |
| `config/costmap_global.yaml` | 全局代价地图参数 |
| `config/costmap_local.yaml` | 局部代价地图参数 |
| `config/move_base.yaml` | move_base 导航参数 (DWA) |
| `config/explore_lite.yaml` | explore_lite 全自主探索参数 |

### 关键 ROS 话题

| 话题 | 类型 | 说明 |
|------|------|------|
| `/cmd_vel` | `geometry_msgs/Twist` | 速度控制指令（输入） |
| `/camera/color/image_raw` | `sensor_msgs/Image` | D435 彩色图 |
| `/camera/aligned_depth_to_color/image_raw` | `sensor_msgs/Image` | D435 对齐深度图 |
| `/camera/color/camera_info` | `sensor_msgs/CameraInfo` | 相机内参 |
| `/rtabmap/mapData` | `rtabmap_msgs/MapData` | RTAB-Map 地图数据 |
| `/rtabmap/grid_map` | `nav_msgs/OccupancyGrid` | 2D 占据栅格地图 |
| `/ultrasonic_distance` | `std_msgs/UInt16` | 超声波测距结果（mm） |

---

## 📖 使用指南

### 串口直连测试（无需 ROS）

```bash
screen /dev/ttyUSB0 115200
```

| 命令 | 功能 |
|------|------|
| `H` | 显示帮助菜单 |
| `D` | 超声波测距 |
| `A` | 切换到自主避障模式 |
| `M` | 切换到手动模式 |
| `F 50` | 前进 |
| `S` | 停止 |

退出 screen: `Ctrl+A` → `K`

### ROS 遥控测试

```bash
# 终端1
source scripts/setup_env.sh
rosrun orbbec_gemini_slam stm32_serial_bridge.py

# 终端2
source /opt/ros/noetic/setup.bash
rostopic pub /cmd_vel geometry_msgs/Twist '{linear: {x: 0.3}}' -r 3
rostopic pub /cmd_vel geometry_msgs/Twist '{linear: {x: 0}}' -1   # 停车
```

### SLAM 建图

```bash
# 一键启动（推荐）
bash scripts/start_slam.sh

# 或手动启动
source scripts/setup_env.sh
roslaunch orbbec_gemini_slam zystm32_slam.launch
```

**键盘控制：**

| 按键 | 动作 |
|------|------|
| `W` / `S` | 前进 / 后退 |
| `A` / `D` | 左转 / 右转 |
| `Q` / `E` | 原地左旋 / 原地右旋 |
| `Space` | 停止 |
| `+` / `-` | 加速 / 减速 |
| `ESC` | 退出并保存地图 |

**RTAB-Map 可视化颜色说明：**

| 颜色 | 含义 |
|------|------|
| 🔴 红色 | 当前帧实时扫描（正在建图，正常！） |
| ⬜ 灰白色 | 已建好的地图点云 |
| 🟢 绿色 | 回环检测匹配上的特征 |
| 🔵 蓝色 | 全局回环闭合边 |

### 地图保存与导出

```bash
# 地图自动保存位置
ls ~/.ros/rtabmap.db

# 查看地图
rtabmap-databaseViewer ~/.ros/rtabmap.db

# 导出 3D 点云
rtabmap-export --cloud ~/.ros/rtabmap.db --output map.ply

# 导出 2D 占据栅格地图
rtabmap-export --grid ~/.ros/rtabmap.db --output map_grid
```

---

## 📡 串口协议

STM32 固件通过 USART1 (115200bps, 8N1, `\r\n` 结尾) 与上位机通信。

### 命令列表

| 命令 | 参数 | 功能 |
|------|------|------|
| `F <speed>` | 0-100 | 前进 |
| `B <speed>` | 0-100 | 后退 |
| `L <speed>` | 0-100 | 左转 |
| `R <speed>` | 0-100 | 右转 |
| `SL <speed>` | 0-100 | 原地左旋 |
| `SR <speed>` | 0-100 | 原地右旋 |
| `S` | — | 停止 |
| `G <angle>` | 0-180° | 舵机角度（90=前，175=左，5=右） |
| `D` | — | 超声波测距，返回 `D <mm>` |
| `A` | — | 切换到自主避障模式 |
| `M` | — | 切换到手动模式（ROS/串口控制） |
| `H` | — | 显示帮助菜单 |

### 示例

```
F 50\r\n    → 前进 50% 速度
SL 80\r\n   → 原地左旋 80% 速度
G 90\r\n    → 舵机转到前方
D\r\n       → 测距，回复 D 234 (234mm)
```

### ROS 桥接映射

`stm32_serial_bridge.py` 将 ROS `Twist` 消息映射为串口命令：

| Twist 输入 | 串口命令 |
|-----------|---------|
| `linear.x > 0.02` | `F <speed>` |
| `linear.x < -0.02` | `B <speed>` |
| `angular.z > 0.05, linear.x ≈ 0` | `SL <speed>` |
| `angular.z < -0.05, linear.x ≈ 0` | `SR <speed>` |
| `angular.z > 0, linear.x > 0` | `L <speed>` |
| `angular.z < 0, linear.x > 0` | `R <speed>` |
| `linear.x ≈ 0, angular.z ≈ 0` | `S` |

---

## 🔄 模式切换

ZYSTM32-A1 支持三种模式切换方式：

| 方式 | 切到 MANUAL | 切到 AUTO |
|------|------------|----------|
| **按键** | 按一下 KEY（蜂鸣器响） | 再按一下 KEY |
| **自动** | ROS 发运动指令时 | 5 秒无 ROS 指令 |
| **串口命令** | 发 `M` 回车 | 发 `A` 回车 |

**LED 指示：**
- **D4 LED 亮** = AUTO 模式（超声波舵机扫描避障中）
- **D3 LED 亮** = MANUAL 模式（等待 ROS 或串口指令）

> 💡 **最佳实践：** 按一下按键切 MANUAL → 键盘遥控建图 → 按一下切回 AUTO 避障。

---

## 📁 项目文件结构

```
ZYSTM32-A1/
├── install.sh                    ← 一键部署脚本（安装依赖+编译）
├── firmware/                     ← STM32 下位机固件
│   ├── USER/                     ← 用户代码入口
│   │   ├── main.c               ← 主程序（435行）：串口解析、避障、模式切换
│   │   ├── Makefile             ← 编译 + 一键烧录
│   │   ├── stm32f103ve_flash.ld ← 链接脚本（256K Flash / 48K RAM）
│   │   ├── flash_auto.py        ← 自动烧录脚本（免跳线帽）
│   │   └── stm32f10x_it.c       ← 中断服务函数
│   ├── SYSTEM/                   ← 系统级驱动
│   │   ├── motor/               ← 电机驱动 (PWM, 4路)
│   │   ├── usart/               ← 串口通信（含 _write 修复）
│   │   ├── UltrasonicWave/      ← 超声波 HC-SR04 驱动
│   │   ├── Server/              ← 舵机 PWM 驱动
│   │   ├── IRAvoid/             ← 红外避障传感器
│   │   ├── IRSEARCH/            ← 红外循迹
│   │   ├── delay/               ← 延时函数
│   │   ├── TIMER/               ← 定时器配置
│   │   ├── keysacn/             ← 按键扫描
│   │   └── sys/                 ← 系统配置
│   ├── CORE/                     ← Cortex-M3 内核文件
│   │   ├── core_cm3.h/c         ← CMSIS 内核抽象层
│   │   └── startup_stm32f10x_hd.s ← 启动文件（GNU 汇编语法）
│   └── STM32F10x_FWLib/         ← STM32 标准外设库 v3.5
│       ├── inc/                 ← 外设头文件
│       └── src/                 ← 外设源文件
│
├── ros_ws/                       ← ROS 工作区
│   └── src/orbbec_gemini_slam/  ← ROS 功能包
│       ├── launch/              ← 启动文件（8个 .launch）
│       ├── scripts/             ← Python 节点（6个）+ 测试脚本
│       ├── config/              ← RViz 配置 + 相机标定 + 导航参数
│       ├── CMakeLists.txt       ← ROS 编译配置
│       └── package.xml          ← 功能包描述
│
├── scripts/                      ← 环境配置与启动脚本
│   ├── run.sh                   ← 统一入口（交互式菜单 / 直接命令）
│   ├── setup_env.sh             ← source 它配置 ROS 环境
│   └── start_slam.sh            ← 一键启动 SLAM
│
├── tools/                        ← 测试工具
│   ├── test_stm32.py            ← 串口通信测试
│   ├── test_stm32.sh            ← 串口测试（bash 版）
│   └── test_motor.py            ← 电机直连测试
│
├── docs/                         ← 文档
│   ├── ZYSTM32-烧录流程.md      ← 烧录详细说明
│   ├── ZYSTM32-SLAM-任务存档.md ← 开发历程与 Bug 修复记录
│   └── STM32-ROS-测试命令.txt   ← 完整测试命令参考
│
├── README.md                     ← 本文件
├── LICENSE                       ← 许可证
└── ZYSTM32-A1-测试指南.txt       ← 快速测试指南
```

---

## 🐛 常见故障排查

### STM32 无响应

```
screen /dev/ttyUSB0 115200
# 输入 H 回车，无输出
```

- 检查 USB 线是否插好
- 检查电池开关是否打开
- 检查 `ls /dev/ttyUSB*` 设备是否存在
- 拔插 STM32 USB 线后按 RESET

### ROS 报 "package not found"

```bash
# 必须 source 环境
source /opt/ros/noetic/setup.bash
source ros_ws/devel/setup.bash

# 或使用项目脚本
source scripts/setup_env.sh
```

### ROS 桥接连不上串口

```bash
# test_ros_bridge.sh 使用了 systemd-run 绕过权限
cd ros_ws/src/orbbec_gemini_slam/scripts
bash test_ros_bridge.sh
```

### 小车运动异常

- **D4 LED 亮** = AUTO 避障中（正常）
- **D3 LED 亮** = MANUAL 等待指令
- 紧急停车：按 KEY 或发 `S` 回车

### 烧录失败

```
# 先停掉占用串口的进程（如 ROS 桥接）
# 再重新烧录
make flash
```

### roscore 报缓存错误

```bash
rospack profile
```

---

## 📋 已修复 Bug 记录

| # | 文件 | 问题 | 修复 |
|---|------|------|------|
| 1 | `stm32f103ve_flash.ld` | 链接脚本按 F103VE (512K/64K) 配置，实际芯片是 F103VC (256K/48K) | 修正 Flash/RAM 大小，`_estack` 在 RAM 范围内 |
| 2 | `usart.c` | GCC newlib 环境下 `printf` 无输出 | 添加 `_write()` syscall 函数 |
| 3 | `stm32_serial_bridge.py` | 打开串口时 DTR 拉低导致 STM32 复位 | `ser.dtr = False; ser.rts = False` |
| 4 | `motor.c` | `cSpeed == 0` 时方向引脚状态不定 | 添加 `else` 分支，停止时方向引脚置低 |
| 5 | `main.c` | `sscanf` 解析命令时缓冲区无空终止符 | 解析前 `buf[len] = 0` |
| 6 | `main.c` | `B`（后退）命令速度映射反向 | `speed = 100 - speed` |
| 7 | `stm32_serial_bridge.py` | 串口缓冲溢出导致命令堆积 | 10Hz 发送 + 每次清输出缓冲 |
| 8 | `keyboard_teleop.py` | 原地旋转速度太快 | Q/E 从 0.8 → 0.4 rad/s |

---

## 🗺️ 开发计划

- [x] STM32 超声波舵机避障
- [x] ROS 串口桥接通信
- [x] RTAB-Map RGB-D SLAM 建图
- [x] 键盘遥控
- [x] 模式切换（AUTO/MANUAL）
- [x] 自动探索导航（explore_lite + move_base）
- [x] 基于已建地图的导航（move_base + 路径规划）
- [ ] Web 端遥控界面
- [ ] 多机器人协同建图
- [ ] 2D LiDAR 融合（RPLIDAR 等）

---

## 📜 许可证

本项目基于 [MIT License](LICENSE) 开源。

STM32 标准外设库 (STM32F10x_FWLib) 版权归 STMicroelectronics 所有。

---

## 🙏 致谢

- 智宇科技 — ZYSTM32-A1 亚克力四驱机器人底盘
- Intel RealSense — D435 深度相机
- ROS Community — Robot Operating System
- RTAB-Map Team — Real-Time Appearance-Based Mapping
- arm-none-eabi-gcc — ARM Cortex-M 交叉编译工具链

---

<div align="center">
  <sub>Built with ❤️ for robotics enthusiasts</sub>
</div>
