/*******************************************************************************
 * ZYSTM32-A1 全自主分工会作版固件
 *
 * 架构：
 *   ROS 上位机通过串口发高级指令（F/B/L/R/SL/SR/S）
 *   STM32 执行指令的同时，用红外+超声波做安全层检测
 *   一旦检测到近距离障碍，STM32 自主避障（覆盖 ROS 指令）
 *
 * 串口协议 (115200bps, 8N1, 以 \r\n 结尾):
 *   F <speed>  前进
 *   B <speed>  后退
 *   L <speed>  左转
 *   R <speed>  右转
 *   SL <speed> 原地左旋
 *   SR <speed> 原地右旋
 *   S          停止
 *   G <angle>  舵机角度 (0-180)
 *   D          查询超声波距离
 *   H          帮助
 *
 * 安全层（非阻塞状态机，不影响串口响应）：
 *   红外左 (PA8) + 红外右 (PB1) → 局部避障
 *   超声波 (PC0/PC1)           → 前方紧急停车
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

// ==================== 红外传感器定义 ====================

#define IR_LEFT_PORT    GPIOA
#define IR_LEFT_PIN     GPIO_Pin_8
#define IR_RIGHT_PORT   GPIOB
#define IR_RIGHT_PIN    GPIO_Pin_1

#define BARRIER_Y   0   // 有障碍（低电平）
#define BARRIER_N   1   // 无障碍（高电平，上拉）

static void IR_Init(void)
{
    GPIO_InitTypeDef g;
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOA | RCC_APB2Periph_GPIOB, ENABLE);
    g.GPIO_Mode = GPIO_Mode_IPU;
    g.GPIO_Speed = GPIO_Speed_50MHz;
    g.GPIO_Pin = IR_LEFT_PIN;
    GPIO_Init(IR_LEFT_PORT, &g);
    g.GPIO_Pin = IR_RIGHT_PIN;
    GPIO_Init(IR_RIGHT_PORT, &g);
}

static uint8_t ir_left(void)  { return GPIO_ReadInputDataBit(IR_LEFT_PORT,  IR_LEFT_PIN);  }
static uint8_t ir_right(void) { return GPIO_ReadInputDataBit(IR_RIGHT_PORT, IR_RIGHT_PIN); }

// ==================== 电机控制 ====================

static signed char g_left_speed = 0;
static signed char g_right_speed = 0;

static void apply_motion(signed char left, signed char right)
{
    g_left_speed = left;
    g_right_speed = right;
    SetMotorSpeed(1, left);   // 左轮
    SetMotorSpeed(0, right);  // 右轮
}

static void cmd_stop(void)
{
    apply_motion(0, 0);
}

// ==================== 串口命令解析 ====================

static void process_command(void)
{
    char *buf = (char *)USART_RX_BUF;
    int len = USART_RX_STA & 0x3FFF;
    int speed, angle;

    buf[len] = 0;
    if (len < 1) return;

    switch (buf[0])
    {
        case 'F':  // 前进
            if (sscanf(buf+1, "%d", &speed) == 1) {
                if (speed < 0) speed = 0;
                if (speed > 100) speed = 100;
                apply_motion(-speed, speed);
                printf("OK F %d\r\n", speed);
            }
            break;

        case 'B':  // 后退
            if (sscanf(buf+1, "%d", &speed) == 1) {
                if (speed < 0) speed = 0;
                if (speed > 100) speed = 100;
                speed = 100 - speed;
                apply_motion(speed, -speed);
                printf("OK B %d\r\n", speed);
            }
            break;

        case 'L':  // 左转
            if (buf[1] == ' ' || buf[1] == '\t') {
                if (sscanf(buf+1, "%d", &speed) == 1) {
                    if (speed < 0) speed = 0;
                    if (speed > 100) speed = 100;
                    apply_motion(0, speed);
                    printf("OK L %d\r\n", speed);
                }
            }
            break;

        case 'R':  // 右转
            if (sscanf(buf+1, "%d", &speed) == 1) {
                if (speed < 0) speed = 0;
                if (speed > 100) speed = 100;
                apply_motion(-speed, 0);
                printf("OK R %d\r\n", speed);
            }
            break;

        case 'S':
            if (len >= 2 && buf[1] == 'L') {  // 原地左旋
                if (sscanf(buf+2, "%d", &speed) == 1) {
                    if (speed < 0) speed = 0;
                    if (speed > 100) speed = 100;
                    apply_motion(speed, 100 - speed);
                    printf("OK SL %d\r\n", speed);
                }
            }
            else if (len >= 2 && buf[1] == 'R') {  // 原地右旋
                if (sscanf(buf+2, "%d", &speed) == 1) {
                    if (speed < 0) speed = 0;
                    if (speed > 100) speed = 100;
                    apply_motion(-(100 - speed), -speed);
                    printf("OK SR %d\r\n", speed);
                }
            }
            else {  // 停止
                cmd_stop();
                printf("OK S\r\n");
            }
            break;

        case 'G':  // 舵机
            if (sscanf(buf+1, "%d", &angle) == 1) {
                if (angle < 0) angle = 0;
                if (angle > 180) angle = 180;
                SetJointAngle(angle);
                delay_ms(100);
                printf("OK G %d\r\n", angle);
            }
            break;

        case 'D':  // 测距
            {
                int dist = UltrasonicWave_StartMeasure();
                printf("D %d\r\n", dist);
            }
            break;

        case 'H':  // 帮助
            printf("=== ZYSTM32-A1 Auto Explore ===\r\n");
            printf("F/B/L/R/SL/SR/S  speed 0-100\r\n");
            printf("G angle 0-180 | D distance | H help\r\n");
            printf("Safety: IR+US avoid enabled\r\n");
            printf("OK H\r\n");
            break;

        default:
            printf("ERR unknown cmd: %s\r\n", buf);
            break;
    }
}

// ==================== 安全层：红外+超声波避障 ====================

#define SAFE_DISTANCE_MM    250    // 超声波安全距离 (mm) = 25cm
#define AVOID_BACK_TIME     30     // 后退节拍数 (~900ms @ 30ms/tick)
#define AVOID_TURN_TIME     15     // 转向节拍数 (~450ms @ 30ms/tick)

typedef enum {
    SAFE_NORMAL,        // 正常模式：ROS 控制
    SAFE_STOP,          // 检测到障碍→停车
    SAFE_BACKUP,        // 后退
    SAFE_TURN,          // 转向避开
} safe_state_t;

static safe_state_t safe_state = SAFE_NORMAL;
static uint16_t safe_tick = 0;
static int safe_turn_dir = 1;  // 1=左转, -1=右转

static void safety_layer(void)
{
    uint8_t il = ir_left();
    uint8_t ir = ir_right();
    int dist = UltrasonicWave_StartMeasure();  // 触发一次测距

    switch (safe_state)
    {
    case SAFE_NORMAL:
        // ── 超声波前方检测 ──
        if (dist > 0 && dist < SAFE_DISTANCE_MM) {
            safe_state = SAFE_STOP;
            safe_tick = 0;
            apply_motion(0, 0);
            printf("! US %dmm\r\n", dist);
            break;
        }

        // ── 红外避障 ──
        if (il == BARRIER_Y && ir == BARRIER_Y) {
            // 两侧都有障碍 → 后退掉头
            safe_state = SAFE_STOP;
            safe_tick = 0;
            safe_turn_dir = 1;  // 默认左转
            apply_motion(0, 0);
            printf("! IR BOTH\r\n");
        }
        else if (il == BARRIER_Y && ir == BARRIER_N) {
            // 左侧有障碍 → 右转避开
            apply_motion(-50, 0);   // 临时覆盖：右转
            printf("! IR LEFT\r\n");
        }
        else if (il == BARRIER_N && ir == BARRIER_Y) {
            // 右侧有障碍 → 左转避开
            apply_motion(0, 50);    // 临时覆盖：左转
            printf("! IR RIGHT\r\n");
        }
        // 无障碍 → 不做任何事，让 ROS 指令控制
        break;

    case SAFE_STOP:
        // 停车 200ms 后开始后退
        if (safe_tick++ > 6) {  // ~180ms
            safe_state = SAFE_BACKUP;
            safe_tick = 0;
            apply_motion(40, -40);  // 后退
            printf("  back\r\n");
        }
        break;

    case SAFE_BACKUP:
        if (safe_tick++ > AVOID_BACK_TIME) {
            safe_state = SAFE_TURN;
            safe_tick = 0;
            // 转向：往无障碍一侧转
            uint8_t il_now = ir_left();
            uint8_t ir_now = ir_right();
            if (il_now == BARRIER_N && ir_now == BARRIER_Y) {
                safe_turn_dir = -1;  // 右转（右侧有障）
            } else {
                safe_turn_dir = 1;   // 左转
            }
            if (safe_turn_dir > 0) {
                apply_motion(60, 40);   // 原地左旋
            } else {
                apply_motion(-40, -60); // 原地右旋
            }
            printf("  turn %s\r\n", safe_turn_dir > 0 ? "L" : "R");
        }
        break;

    case SAFE_TURN:
        if (safe_tick++ > AVOID_TURN_TIME) {
            safe_state = SAFE_NORMAL;
            safe_tick = 0;
            // 恢复：让 ROS 重新控制
            printf("! resume\r\n");
        }
        break;
    }
}

// ==================== 主函数 ====================

int main(void)
{
    delay_init();
    KEY_Init();
    IR_Init();                              // 红外初始化
    Timerx_Init(5000, 7199);                // 10KHz 计数，500ms 定时
    UltrasonicWave_Configuration();         // 超声波初始化
    uart_init(115200);                      // 串口
    TIM4_PWM_Init(7199, 0);                 // 电机 PWM 10KHz
    TIM5_PWM_Init(9999, 143);               // 舵机 PWM 50Hz
    ZYSTM32_brake(500);                     // 初始刹车

    printf("\r\n=== ZYSTM32-A1 Auto Explore ===\r\n");
    printf("ROS + STM32 Safety Layer Ready\r\n");
    printf("Send 'H' for help.\r\n");

    while (1)
    {
        // ── 1. 处理串口命令（ROS 指令）──
        if (USART_RX_STA & 0x8000)
        {
            process_command();
            USART_RX_STA = 0;  // 清标志，准备收下一条
        }

        // ── 2. 安全层检查（非阻塞，覆盖 ROS 指令）──
        safety_layer();

        delay_ms(30);  // ~33Hz 主循环
    }
}
