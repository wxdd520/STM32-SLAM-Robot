#ifndef __IRAVOID_H_
#define __IRAVOID_H_

#include "stm32f10x.h"                  // Device header

void IRAvoidInit(void);
void AVoidRun(void);

//避障传感器
/* 
避障传感器 AVOID_PIN	PB1
 */

#define AVOID_RIGHT_PIN         GPIO_Pin_1
#define AVOID_RIGHT_PIN_GPIO    GPIOB
#define AVOID_RIGHT_IO          GPIO_ReadInputDataBit(AVOID_RIGHT_PIN_GPIO, AVOID_RIGHT_PIN)

#define AVOID_LEFT_PIN         GPIO_Pin_8
#define AVOID_LEFT_PIN_GPIO    GPIOA
#define AVOID_LEFT_IO          GPIO_ReadInputDataBit(AVOID_LEFT_PIN_GPIO, AVOID_LEFT_PIN)



#define BARRIER_Y 0      //有障碍物
#define BARRIER_N 1      //无障碍物



#endif
