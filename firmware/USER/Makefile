###############################################################################
# Makefile for ZYSTM32-A1 SLAM firmware
# Target: STM32F103VE (High Density), arm-none-eabi-gcc
# 
# Usage:
#   make          build firmware
#   make flash    flash via stm32flash (USB serial bootloader)
#   make clean    clean build artifacts
###############################################################################

# Project name
TARGET = zystm32_a1_slam

# Toolchain
PREFIX = arm-none-eabi-
CC     = $(PREFIX)gcc
AS     = $(PREFIX)gcc -x assembler-with-cpp
OBJCOPY = $(PREFIX)objcopy
OBJDUMP = $(PREFIX)objdump
SIZE   = $(PREFIX)size

# Project root (parent of USER)
PRJ_ROOT = ..

# Source directories
VPATH += $(PRJ_ROOT)/USER
VPATH += $(PRJ_ROOT)/CORE
VPATH += $(PRJ_ROOT)/SYSTEM/delay
VPATH += $(PRJ_ROOT)/SYSTEM/IRAvoid
VPATH += $(PRJ_ROOT)/SYSTEM/IRSEARCH
VPATH += $(PRJ_ROOT)/SYSTEM/keysacn
VPATH += $(PRJ_ROOT)/SYSTEM/motor
VPATH += $(PRJ_ROOT)/SYSTEM/Server
VPATH += $(PRJ_ROOT)/SYSTEM/sys
VPATH += $(PRJ_ROOT)/SYSTEM/TIMER
VPATH += $(PRJ_ROOT)/SYSTEM/UltrasonicWave
VPATH += $(PRJ_ROOT)/SYSTEM/usart
VPATH += $(PRJ_ROOT)/STM32F10x_FWLib/src

# Include paths
INCLUDES  = -I$(PRJ_ROOT)/USER
INCLUDES += -I$(PRJ_ROOT)/CORE
INCLUDES += -I$(PRJ_ROOT)/SYSTEM/delay
INCLUDES += -I$(PRJ_ROOT)/SYSTEM/IRAvoid
INCLUDES += -I$(PRJ_ROOT)/SYSTEM/IRSEARCH
INCLUDES += -I$(PRJ_ROOT)/SYSTEM/keysacn
INCLUDES += -I$(PRJ_ROOT)/SYSTEM/motor
INCLUDES += -I$(PRJ_ROOT)/SYSTEM/Server
INCLUDES += -I$(PRJ_ROOT)/SYSTEM/sys
INCLUDES += -I$(PRJ_ROOT)/SYSTEM/TIMER
INCLUDES += -I$(PRJ_ROOT)/SYSTEM/UltrasonicWave
INCLUDES += -I$(PRJ_ROOT)/SYSTEM/usart
INCLUDES += -I$(PRJ_ROOT)/STM32F10x_FWLib/inc

# Source files (USER)
SRCS_USER  = main.c
SRCS_USER += stm32f10x_it.c
SRCS_USER += system_stm32f10x.c

# Source files (CORE)
SRCS_CORE  = 
SRCS_CORE += startup_stm32f10x_hd.s

# Source files (SYSTEM)
SRCS_SYS  = delay.c
SRCS_SYS += IRAvoid.c
SRCS_SYS += IRSEARCH.c
SRCS_SYS += keysacn.c
SRCS_SYS += motor.c
SRCS_SYS += Server.c
SRCS_SYS += sys.c
SRCS_SYS += timer.c
SRCS_SYS += UltrasonicWave.c
SRCS_SYS += usart.c

# Source files (FWLib) - only the ones actually used
SRCS_FWLIB  = misc.c
SRCS_FWLIB += stm32f10x_exti.c
SRCS_FWLIB += stm32f10x_flash.c
SRCS_FWLIB += stm32f10x_gpio.c
SRCS_FWLIB += stm32f10x_rcc.c
SRCS_FWLIB += stm32f10x_tim.c
SRCS_FWLIB += stm32f10x_usart.c

# All source files
SRCS = $(SRCS_USER) $(SRCS_CORE) $(SRCS_SYS) $(SRCS_FWLIB)

# Object files
OBJS = $(SRCS:.c=.o)
OBJS := $(OBJS:.s=.o)
OBJS := $(addprefix build/,$(notdir $(OBJS)))

# MCU flags
MCU_FLAGS = -mcpu=cortex-m3 -mthumb

# Compiler flags
CFLAGS  = $(MCU_FLAGS)
CFLAGS += $(INCLUDES)
CFLAGS += -DUSE_STDPERIPH_DRIVER
CFLAGS += -DSTM32F10X_HD
CFLAGS += -DHSE_VALUE=8000000
CFLAGS += -Os
CFLAGS += -Wall -Wno-unused-parameter -Wno-unused-variable
CFLAGS += -ffunction-sections -fdata-sections
CFLAGS += -g

# Linker flags
LDFLAGS  = $(MCU_FLAGS)
LDFLAGS += -Tstm32f103ve_flash.ld
LDFLAGS += -Wl,--gc-sections
LDFLAGS += -Wl,-Map=$(TARGET).map
LDFLAGS += -specs=nano.specs -specs=nosys.specs

# Libraries
LIBS = -lc -lm -lnosys

# Default target
all: $(TARGET).elf $(TARGET).bin $(TARGET).hex

# Create build directory
build:
	mkdir -p build

# Compile C files
build/%.o: %.c | build
	$(CC) $(CFLAGS) -c $< -o $@

# Compile assembly files
build/%.o: %.s | build
	$(AS) $(CFLAGS) -c $< -o $@

# Link
$(TARGET).elf: $(OBJS)
	$(CC) $(LDFLAGS) $(OBJS) $(LIBS) -o $@
	$(SIZE) $@

# Generate binary
$(TARGET).bin: $(TARGET).elf
	$(OBJCOPY) -O binary $< $@

$(TARGET).hex: $(TARGET).elf
	$(OBJCOPY) -O ihex $< $@

# Flash via STM32 serial bootloader — auto RTS/DTR (no jumper needed!)
flash: $(TARGET).bin
	@python3 flash_auto.py

# Clean
clean:
	rm -rf build $(TARGET).elf $(TARGET).bin $(TARGET).hex $(TARGET).map

.PHONY: all clean flash
