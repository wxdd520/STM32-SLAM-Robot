/*******************************************************************************
 * ZYSTM32-A1 超声波+舵机避障 + ROS 串口指令
 *
 * 架构：
 *   默认模式：超声波舵机扫描（前/左/右）+ 自动避障
 *   ROS 模式：收到串口指令后切换到 ROS 控制
 *   3 秒无 ROS 指令 → 自动回到超声波避障模式
 *
 * 舵机扫描方向：
 *   前方: 90°     左侧: 175°     右侧: 5°
 *
 * 避障逻辑（来自例程7）：
 *   前方 < 60mm → 刹车 → 后退 → 扫描左右 → 往开阔侧转
 *   前方 ≥ 60mm → 前进
 *
 * 串口协议 (115200bps, 8N1, 以 \r\n 结尾):
 *   F/B/L/R/SL/SR/S  speed 0-100
 *   G <angle>  舵机角度
 *   D          测距
 *   A          切换到自主避障模式
 *   M          切换到手动模式（ROS控制）
 *   H          帮助
 ******************************************************************************/

#include "stm32f10x.h"
#include "delay.h"
#include "motor.h"
#include "usart.h"
#include "UltrasonicWave.h"
#include "timer.h"
#include "Server.h"
#include "string.h"
#include "stdio.h"

// ==================== 超声波舵机扫描 ====================

static int front_detection(void)
{
    SetJointAngle(90);
    delay_ms(200);
    return UltrasonicWave_StartMeasure();
}

static int left_detection(void)
{
    SetJointAngle(175);
    delay_ms(400);
    return UltrasonicWave_StartMeasure();
}

static int right_detection(void)
{
    SetJointAngle(5);
    delay_ms(400);
    return UltrasonicWave_StartMeasure();
}

// ==================== 电机控制（非阻塞） ====================

static signed char g_left_speed  = 0;
static signed char g_right_speed = 0;

static void apply_motion(signed char left, signed char right)
{
    g_left_speed  = left;
    g_right_speed = right;
    SetMotorSpeed(1, left);   // 左轮
    SetMotorSpeed(0, right);  // 右轮
}

static void cmd_stop(void) { apply_motion(0, 0); }

// ==================== 模式选择 ====================

typedef enum {
    MODE_AUTO,    // 超声波自主避障
    MODE_MANUAL,  // ROS 串口控制
} mode_t;

static mode_t g_mode = MODE_AUTO;
static uint32_t g_last_ros_cmd_tick = 0;  // 最后一次收到 ROS 指令的时间
#define ROS_TIMEOUT_TICK  100   // ~3秒 (100 × 30ms)

// ==================== 串口命令解析 ====================

static void process_command(void)
{
    char *buf = (char *)USART_RX_BUF;
    int len = USART_RX_STA & 0x3FFF;
    int speed, angle;

    buf[len] = 0;
    if (len < 1) return;

    // 收到任何运动指令都切换到手动模式并刷新计时
    if (buf[0] == 'F' || buf[0] == 'B' || buf[0] == 'L' ||
        buf[0] == 'R' || buf[0] == 'S')
    {
        g_mode = MODE_MANUAL;
        g_last_ros_cmd_tick = 0;
    }

    switch (buf[0])
    {
        case 'F':
            if (sscanf(buf+1, "%d", &speed) == 1) {
                if (speed < 0) speed = 0;
                if (speed > 100) speed = 100;
                apply_motion(-speed, speed);
                printf("OK F %d\r\n", speed);
            }
            break;

        case 'B':
            if (sscanf(buf+1, "%d", &speed) == 1) {
                if (speed < 0) speed = 0;
                if (speed > 100) speed = 100;
                speed = 100 - speed;
                apply_motion(speed, -speed);
                printf("OK B %d\r\n", speed);
            }
            break;

        case 'L':
            if (buf[1] == ' ' || buf[1] == '\t') {
                if (sscanf(buf+1, "%d", &speed) == 1) {
                    if (speed < 0) speed = 0;
                    if (speed > 100) speed = 100;
                    apply_motion(0, speed);
                    printf("OK L %d\r\n", speed);
                }
            }
            break;

        case 'R':
            if (sscanf(buf+1, "%d", &speed) == 1) {
                if (speed < 0) speed = 0;
                if (speed > 100) speed = 100;
                apply_motion(-speed, 0);
                printf("OK R %d\r\n", speed);
            }
            break;

        case 'S':
            if (len >= 2 && buf[1] == 'L') {
                if (sscanf(buf+2, "%d", &speed) == 1) {
                    if (speed < 0) speed = 0;
                    if (speed > 100) speed = 100;
                    apply_motion(speed, 100 - speed);
                    printf("OK SL %d\r\n", speed);
                }
            }
            else if (len >= 2 && buf[1] == 'R') {
                if (sscanf(buf+2, "%d", &speed) == 1) {
                    if (speed < 0) speed = 0;
                    if (speed > 100) speed = 100;
                    apply_motion(-(100 - speed), -speed);
                    printf("OK SR %d\r\n", speed);
                }
            }
            else {
                cmd_stop();
                printf("OK S\r\n");
            }
            break;

        case 'G':
            if (sscanf(buf+1, "%d", &angle) == 1) {
                if (angle < 0) angle = 0;
                if (angle > 180) angle = 180;
                SetJointAngle(angle);
                delay_ms(100);
                printf("OK G %d\r\n", angle);
            }
            break;

        case 'D':
            {
                int dist = UltrasonicWave_StartMeasure();
                printf("D %d\r\n", dist);
            }
            break;

        case 'A':  // 切换到自主避障模式
            g_mode = MODE_AUTO;
            printf("OK AUTO\r\n");
            break;

        case 'M':  // 切换到手动模式
            g_mode = MODE_MANUAL;
            g_last_ros_cmd_tick = 0;
            printf("OK MANUAL\r\n");
            break;

        case 'H':
            printf("=== ZYSTM32-A1 SONIC+ROS ===\r\n");
            printf("F/B/L/R/SL/SR/S  speed 0-100\r\n");
            printf("G angle 0-180 | D: distance\r\n");
            printf("A: auto avoid | M: manual | H: help\r\n");
            printf("OK H\r\n");
            break;

        default:
            printf("ERR unknown: %s\r\n", buf);
            break;
    }
}

// ==================== 自主避障状态机（非阻塞） ====================

#define SAFE_DIST     60    // 安全距离 mm

typedef enum {
    AVOID_SCAN,       // 舵机看前方
    AVOID_FORWARD,    // 前进
    AVOID_STOP,       // 停车
    AVOID_BACK,       // 后退
    AVOID_SCAN_LR,    // 舵机扫左右
    AVOID_TURN,       // 转向
} avoid_state_t;

static avoid_state_t avoid_state = AVOID_SCAN;
static uint16_t avoid_tick = 0;
static int avoid_turn_dir = 1;  // 1=左转, -1=右转

// 阻塞式延时计数（在主循环 tick 中递减）
static int blocking_delay = 0;

static void start_blocking(int ticks)
{
    blocking_delay = ticks;
}

static int is_blocking(void)
{
    if (blocking_delay > 0) {
        blocking_delay--;
        return 1;
    }
    return 0;
}

static void auto_avoid_loop(void)
{
    int dist, L, R;

    if (is_blocking()) return;

    switch (avoid_state)
    {
    case AVOID_SCAN:
        // 舵机转前方，测距
        SetJointAngle(90);
        start_blocking(10);  // 200ms 等舵机到位
        avoid_state = AVOID_FORWARD;
        break;

    case AVOID_FORWARD:
        dist = front_detection();
        if (dist > 0 && dist < SAFE_DIST) {
            // 前方有障碍！
            printf("! SONIC %dmm\r\n", dist);
            cmd_stop();
            start_blocking(17);  // 500ms 刹车
            avoid_state = AVOID_STOP;
        } else {
            // 前方安全 → 前进
            apply_motion(-50, 50);
            avoid_state = AVOID_SCAN;  // 循环检测
        }
        break;

    case AVOID_STOP:
        // 刹车后 → 后退
        apply_motion(40, -40);    // 后退
        start_blocking(17);       // 500ms
        avoid_state = AVOID_BACK;
        printf("  back\r\n");
        break;

    case AVOID_BACK:
        // 后退完 → 刹车 1s
        cmd_stop();
        start_blocking(33);       // 1000ms
        avoid_state = AVOID_SCAN_LR;
        break;

    case AVOID_SCAN_LR:
        // 扫描左右
        L = left_detection();
        delay_ms(500);
        R = right_detection();
        delay_ms(500);

        if (L < SAFE_DIST && R < SAFE_DIST) {
            // 两侧都堵 → 原地左旋
            apply_motion(60, 40);
            start_blocking(33);     // 1000ms 旋转
            printf("  spin L\r\n");
        } else if (L > R) {
            // 左边更开阔 → 左转
            apply_motion(0, 50);
            start_blocking(33);
            printf("  turn L\r\n");
        } else {
            // 右边更开阔 → 右转
            apply_motion(-50, 0);
            start_blocking(33);
            printf("  turn R\r\n");
        }
        avoid_state = AVOID_TURN;
        break;

    case AVOID_TURN:
        // 转完 → 回到扫描
        avoid_state = AVOID_SCAN;
        printf("  resume\r\n");
        break;
    }
}

// ==================== 主函数 ====================

int main(void)
{
    delay_init();
    // 注：自主模式不需要按键、红外、循迹
    Timerx_Init(5000, 7199);                // 10KHz, 500ms 定时
    UltrasonicWave_Configuration();         // 超声波
    uart_init(115200);                      // 串口
    TIM4_PWM_Init(7199, 0);                 // 电机 PWM
    TIM5_PWM_Init(9999, 143);               // 舵机 PWM 50Hz
    ZYSTM32_brake(500);

    printf("\r\n=== ZYSTM32-A1 SONIC+ROS ===\r\n");
    printf("Mode: AUTO (ultrasonic avoid)\r\n");
    printf("Send 'M' for manual, 'H' for help\r\n");

    while (1)
    {
        // ── 1. 处理串口命令 ──
        if (USART_RX_STA & 0x8000)
        {
            process_command();
            USART_RX_STA = 0;
        }

        // ── 2. 模式管理 ──
        if (g_mode == MODE_MANUAL)
        {
            g_last_ros_cmd_tick++;
            if (g_last_ros_cmd_tick > ROS_TIMEOUT_TICK)
            {
                // ROS 长时间不发指令 → 自动回到自主避障
                g_mode = MODE_AUTO;
                avoid_state = AVOID_SCAN;
                blocking_delay = 0;
                printf("! AUTO (timeout)\r\n");
            }
        }

        // ── 3. 自主避障（仅在 AUTO 模式）──
        if (g_mode == MODE_AUTO)
        {
            auto_avoid_loop();
        }

        delay_ms(30);  // ~33Hz
    }
}
