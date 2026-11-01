ROOT := $(abspath ..)
VENDOR ?= $(ROOT)/.tools/vendor
TOOLCHAIN ?= /usr
CC := $(TOOLCHAIN)/bin/arm-none-eabi-gcc
OBJCOPY := $(TOOLCHAIN)/bin/arm-none-eabi-objcopy
SIZE := $(TOOLCHAIN)/bin/arm-none-eabi-size
BUILD := $(ROOT)/build/firmware
HAL := $(VENDOR)/hal
DEVICE := $(VENDOR)/device
CMSIS := $(VENDOR)/cmsis
TUSB := $(VENDOR)/tinyusb
NEWLIB ?= $(TOOLCHAIN)/lib/arm-none-eabi/newlib/thumb/v7e-m+dp/hard
CPU := -mcpu=cortex-m7 -mthumb -mfpu=fpv5-d16 -mfloat-abi=hard
DEFS := -DSTM32H743xx -DUSE_HAL_DRIVER
INCS := -I. -I$(HAL)/Inc -I$(DEVICE)/Include -I$(CMSIS)/CMSIS/Core/Include -I$(TUSB)/src -I$(TOOLCHAIN)/include/newlib
CFLAGS := $(CPU) $(DEFS) $(INCS) -std=c11 -O3 -g3 -Wall -Wextra -Wno-unused-parameter -Wno-misleading-indentation -ffunction-sections -fdata-sections -MMD -MP
HAL_MODULES := hal hal_cortex hal_rcc hal_rcc_ex hal_gpio hal_dma hal_dma_ex hal_pwr hal_pwr_ex hal_flash hal_flash_ex hal_sai hal_sai_ex hal_i2c hal_i2c_ex hal_adc hal_adc_ex
SOURCES := main.c board.c dsp.c ui.c usb_audio.c $(addprefix $(HAL)/Src/stm32h7xx_,$(addsuffix .c,$(HAL_MODULES))) \
 $(DEVICE)/Source/Templates/system_stm32h7xx.c \
 $(TUSB)/src/tusb.c $(TUSB)/src/common/tusb_fifo.c $(TUSB)/src/device/usbd.c $(TUSB)/src/device/usbd_control.c \
 $(TUSB)/src/class/audio/audio_device.c $(TUSB)/src/portable/synopsys/dwc2/dcd_dwc2.c $(TUSB)/src/portable/synopsys/dwc2/dwc2_common.c
STARTUP := $(DEVICE)/Source/Templates/gcc/startup_stm32h743xx.s
OBJECTS := $(addprefix $(BUILD)/,$(notdir $(SOURCES:.c=.o))) $(BUILD)/startup.o
vpath %.c . $(HAL)/Src $(DEVICE)/Source/Templates $(TUSB)/src $(TUSB)/src/common $(TUSB)/src/device $(TUSB)/src/class/audio $(TUSB)/src/portable/synopsys/dwc2
.PHONY: all clean
all: $(BUILD)/voice_pitcher.bin $(BUILD)/voice_pitcher.hex
$(BUILD):
	mkdir -p $@
$(BUILD)/%.o: %.c | $(BUILD)
	$(CC) $(CFLAGS) -c $< -o $@
$(BUILD)/startup.o: $(STARTUP) | $(BUILD)
	$(CC) $(CPU) -c $< -o $@
$(BUILD)/voice_pitcher.elf: $(OBJECTS) linker.ld
	$(CC) $(CPU) -Tlinker.ld -nostartfiles -Wl,--gc-sections,-Map=$(BUILD)/voice_pitcher.map \
	 -B$(NEWLIB)/ --specs=$(NEWLIB)/nosys.specs -L$(NEWLIB) $(OBJECTS) -Wl,--start-group -lc -lm -lnosys -Wl,--end-group -o $@
	$(SIZE) $@
$(BUILD)/%.bin: $(BUILD)/%.elf
	$(OBJCOPY) -O binary $< $@
$(BUILD)/%.hex: $(BUILD)/%.elf
	$(OBJCOPY) -O ihex $< $@
clean:
	rm -f $(BUILD)/*.o $(BUILD)/*.d $(BUILD)/voice_pitcher.*
-include $(OBJECTS:.o=.d)
