# ZYSTM32-A1 STM32 烧录流程（Linux 一键免跳线帽）

## 🔥 一键烧录（推荐，无需拨跳线帽）

CH340 的 RTS/DTR 已连接 STM32 BOOT0/RESET，软件自动控制进 bootloader。

```bash
cd "~/桌面/全自主建图机器人/智宇科技 ZYSTM32-A1 亚克力四驱机器人光盘资料-A/3.例程代码/7、ZYSTM32-A1 智能小车超声波避障实验(有舵机)/USER"

# 改代码后重新编译 + 烧录：
make clean && make && make flash

# 仅烧录（不重新编译）：
make flash
```

流程：RTS/DTR 自动进入 bootloader → 烧录 .bin → 回读校验 → 自动复位运行。
**全程无需拨跳线帽，USB 插着不动即可。**

---

## 🛠 手动跳线帽烧录（备选，软件控制失败时使用）

排针布局：

```
 GND   GND      ← 上排
BOOT1  BOOT0     ← 中排
 3.3V  3.3V     ← 下排
```

| 模式 | BOOT1 | BOOT0 |
|------|-------|-------|
| 🔥 烧录 | 往上 ↔ GND | **往下 ↔ 3.3V** |
| ✅ 运行 | 往上 ↔ GND | 往上 ↔ GND |

**步骤：** 断USB → 跳线帽如上 → 插USB → RESET → `make flash`（或 `bash flash_stm32.sh`）
**烧录后：** 断USB → BOOT0 改回 GND → 插USB → RESET

---

## ✅ 快速测试

```bash
# 一键测试（发送 H 命令 + 读取回复）
~/桌面/test_stm32.sh

# 交互式串口（退出：Ctrl+A → K → Y）
screen /dev/serial/by-id/usb-1a86_USB_Serial-if00-port0 115200
```

预期回复：

```
=== ZYSTM32-A1 SLAM Commands ===
F <0-100>  前进
B <0-100>  后退
L <0-100>  左转
R <0-100>  右转
SL <0-100> 原地左旋
SR <0-100> 原地右旋
S          停止
G <0-180>  舵机角度
D          超声波测距
H          帮助
```

---

## 🔧 已修复问题记录

| 日期 | 问题 | 修复 |
|------|------|------|
| 2025-06-06 | FlyMcu "程序文件不是0x8000000和0x20000000" | 链接脚本 FLASH 512K→256K, RAM 64K→48K |
| 2025-06-06 | 烧录后串口无输出 | usart.c 添加 `_write()` (GCC newlib 需要) |
| 2025-06-06 | 每次烧录需拨跳线帽 | `flash_auto.py` RTS/DTR 自动控制 bootloader |

---

## 📋 串口协议

| 参数 | 值 |
|------|-----|
| 波特率 | 115200 |
| 数据位 | 8 |
| 校验 | 无 |
| 停止位 | 1 |
| 结尾符 | `\r\n` |

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

---

## 🚀 启动 SLAM

```bash
cd ~/桌面/Slam
source setup_orbbec_slam.sh
roslaunch orbbec_gemini_slam zystm32_slam.launch
```
