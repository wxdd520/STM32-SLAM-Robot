#include "IRAvoid.h"
#include "delay.h"
#include "motor.h"
#include "keysacn.h"
#include "stm32f10x.h"                  // Device header

int SR_2;    //右边红外避障传感器状态
int SL_2;    //左边红外壁障传感器状态
void IRAvoidInit(void)
{
	GPIO_InitTypeDef  GPIO_InitStructure;
	RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOB|RCC_APB2Periph_GPIOA , ENABLE);
	
	GPIO_InitStructure.GPIO_Pin = AVOID_RIGHT_PIN;//配置使能GPIO管脚 PB1
	GPIO_InitStructure.GPIO_Mode = GPIO_Mode_IPU;//配置GPIO模式,输入上拉
	GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;//配置GPIO端口速度
	GPIO_Init(AVOID_RIGHT_PIN_GPIO , &GPIO_InitStructure); 
	
  GPIO_InitStructure.GPIO_Pin = AVOID_LEFT_PIN;//配置使能GPIO管脚 PB1
	GPIO_InitStructure.GPIO_Mode = GPIO_Mode_IPU;//配置GPIO模式,输入上拉
	GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;//配置GPIO端口速度
	GPIO_Init(AVOID_LEFT_PIN_GPIO , &GPIO_InitStructure); 
}


void AVoidRun(void)
{
	SR_2 = AVOID_RIGHT_IO;
	SL_2 = AVOID_LEFT_IO;
	if(SL_2 == 1 && SR_2 == 1)
	{
		 ZYSTM32_run(60,10);
		 BEEP_RESET;
     LED_D3_RESET;		
	}
	else if (SL_2 == 1 && SR_2 == 0)
	{
		  ZYSTM32_Right(70,300);
	}
	else if(SR_2 == 1 && SL_2 == 0)
	{
		   ZYSTM32_Left(70,300);
	}
	else
	{
		 BEEP_SET;
     LED_D3_SET;	
	   ZYSTM32_brake(300);//停止300MS
		 ZYSTM32_back(70,1000);//后退400MS
		
		 ZYSTM32_Spin_Left(100,500);//左转500MS
		
				
	}
	
}
