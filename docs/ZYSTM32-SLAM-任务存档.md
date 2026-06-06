# ZYSTM32-A1 SLAM 建图小车 — 任务存档

## 📌 任务状态

| 项目 | 状态 |
|------|------|
| 🔧 STM32 固件修改 (串口命令协议) | ✅ 已完成 |
| 🛠️ Makefile + GCC 编译 | ✅ 编译成功 |
| 🔥 **烧录到 STM32** | ✅ **已完成** — `make flash` 一键免跳线帽 |
| 🤖 ROS 串口桥接节点 | ✅ 已测试通过 |
| 🚀 联合 SLAM 启动文件 | ✅ RTAB-Map Viz + RViz 画面正常 |
| 📷 D435 + RTAB-Map | ✅ 运行中（需插 USB 3.0 蓝色口） |

---

## 🔥 烧录（Linux 直接用 stm32flash）

### 一步烧录

```bash
cd "/home/wxd/桌面/全自主建图机器人/智宇科技 ZYSTM32-A1 亚克力四驱机器人光盘资料-A/3.例程代码/7、ZYSTM32-A1 智能小车超声波避障实验(有舵机)/USER"
make flash
```

### 烧录前必须操作

1. **断开** STM32 板的 USB 线
2. 把 **BOOT0** 跳线帽从 GND 改接到 **VCC**（3.3V）
3. **重新插上** USB 线
4. 按一下板上的 **RESET** 键
5. 运行 `make flash`

### 烧录后

1. 断 USB，把 BOOT0 跳线帽恢复为 **GND**
2. 重新插 USB，按 RESET 启动

### ⚠️ 2025-06-06 修复：芯片型号不匹配

**原因:** 链接脚本按 STM32F103**VE** (512KB/64KB) 写的，但板子实际是 STM32F103**VC** (256KB Flash / 48KB RAM)，`_estack=0x20010000` 超出 48KB RAM。已改为 `FLASH=256K, RAM=48K` → 重新编译。

### 烧录后测试
| 编程后执行 | 勾选 (自动跳转) |

### 烧录完成后测试

用串口助手（115200, 8N1）发送命令测试：
```
H       → 显示帮助
F 50    → 前进
B 30    → 后退
S       → 停止
G 90    → 舵机回中
D       → 超声波测距
```

---

## 🚀 回到 Linux 后启动 SLAM

```bash
# 终端 1: 一键启动
cd ~/桌面/Slam
source setup_orbbec_slam.sh
roslaunch orbbec_gemini_slam zystm32_slam.launch
```

会启动：
1. STM32 串口桥接 (`/cmd_vel` → 串口命令)
2. D435 相机驱动
3. RTAB-Map RGB-D SLAM
4. 键盘遥控 (WASDQE)

### ⚠️ 启动前检查

| 检查项 | 说明 |
|--------|------|
| D435 相机 | **必须插 USB 3.0 蓝色口**（2.0 口无画面） |
| STM32 小车 | USB 线插好 + 电池开关打开 |
| 旧 ROS 进程 | 全部 Ctrl+C 关掉后再启动 |

### 建图操作

| 按键 | 动作 |
|------|------|
| **W** | 前进 |
| **S** | 后退 |
| **A/D** | 左/右转 |
| **Q/E** | 原地左/右旋 |
| **空格** | 停止 |
| **+/-** | 加速/减速 |
| **ESC** | 退出（自动保存地图） |

### RTAB-Map 画面颜色说明

| 颜色 | 含义 |
|------|------|
| 🔴 红色 | 当前帧实时扫描（SLAM 正在看，正常！） |
| ⬜ 灰白色 | 已建好的地图点云 |
| 🟢 绿色 | 回环检测匹配上的特征 |
| 🔵 蓝色 | 全局回环闭合边 |

---

## 📂 项目文件索引

| 文件 | 路径 |
|------|------|
| **STM32 固件 (已修改)** | `~/桌面/全自主建图机器人/.../7、...超声波避障实验(有舵机)/USER/main.c` |
| **Makefile** | `同上目录/Makefile` |
| **链接脚本** | `同上目录/stm32f103ve_flash.ld` |
| **ROS 串口桥接** | `~/桌面/Slam/orbbec_gemini_slam/scripts/stm32_serial_bridge.py` |
| **键盘遥控** | `~/桌面/Slam/orbbec_gemini_slam/scripts/keyboard_teleop.py` |
| **SLAM 启动文件** | `~/桌面/Slam/orbbec_gemini_slam/launch/zystm32_slam.launch` |
| **D435 SLAM 配置** | `~/桌面/Slam/orbbec_gemini_slam/launch/d435i_rtabmap.launch` |
| **ROS 工作区** | `~/桌面/Slam/catkin_ws/` |

---

## 🔧 固件串口协议

命令以 `\r\n` 结尾 (115200bps, 8N1)

| 命令 | 功能 |
|------|------|
| `F <0-100>` | 前进 |
| `B <0-100>` | 后退 |
| `L <0-100>` | 左转 |
| `R <0-100>` | 右转 |
| `SL <0-100>` | 原地左旋 |
| `SR <0-100>` | 原地右旋 |
| `S` | 停止 |
| `G <0-180>` | 舵机角度 |
| `D` | 超声波测距 |
| `H` | 帮助 |
