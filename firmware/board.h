#ifndef VP_BOARD_H
#define VP_BOARD_H
#include "stm32h7xx_hal.h"
#include <stdbool.h>
enum { AUDIO_FRAMES=32, DMA_WORDS=128 };
extern int32_t audio_rx[DMA_WORDS],audio_tx[DMA_WORDS];
extern volatile uint32_t audio_sequence,audio_overruns;
extern I2C_HandleTypeDef oled_i2c;
void board_init(void);
bool board_power_available(void);
void board_audio_start(void);
void board_audio_stop(void);
bool board_audio_running(void);
void board_fatal(void);
#endif
