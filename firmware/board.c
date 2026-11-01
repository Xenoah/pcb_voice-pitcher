#include "board.h"
#include "tusb.h"
#include <string.h>

__attribute__((section(".dma"),aligned(32))) int32_t audio_rx[DMA_WORDS],audio_tx[DMA_WORDS];
volatile uint32_t audio_sequence,audio_overruns;
static SAI_HandleTypeDef sai_tx,sai_rx;
static DMA_HandleTypeDef dma_tx,dma_rx;
I2C_HandleTypeDef oled_i2c;
static ADC_HandleTypeDef adc;
static bool running;
static void check(HAL_StatusTypeDef result) {if(result!=HAL_OK)board_fatal();}
void board_fatal(void) {
    HAL_GPIO_WritePin(GPIOC,GPIO_PIN_6,GPIO_PIN_RESET);
    __disable_irq();for(;;) { GPIOB->ODR^=GPIO_PIN_0;for(volatile unsigned i=0;i<2000000;i++){} }
}
static void pin(GPIO_TypeDef *port,uint32_t pins,uint32_t mode,uint32_t af) {
    GPIO_InitTypeDef g={0};g.Pin=pins;g.Mode=mode;g.Alternate=af;g.Pull=GPIO_NOPULL;g.Speed=GPIO_SPEED_FREQ_HIGH;HAL_GPIO_Init(port,&g);
}
static void cpu_clock(bool fast) {
    RCC_OscInitTypeDef o={0};RCC_ClkInitTypeDef c={0};
    check(HAL_PWREx_ConfigSupply(PWR_LDO_SUPPLY));
    __HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE1);
    while(!__HAL_PWR_GET_FLAG(PWR_FLAG_VOSRDY)){}
    o.OscillatorType=RCC_OSCILLATORTYPE_HSE|RCC_OSCILLATORTYPE_HSI48|RCC_OSCILLATORTYPE_HSI;
    o.HSEState=RCC_HSE_BYPASS;o.HSIState=RCC_HSI_ON;o.HSICalibrationValue=RCC_HSICALIBRATION_DEFAULT;o.HSI48State=RCC_HSI48_ON;
    o.PLL.PLLState=RCC_PLL_ON;o.PLL.PLLSource=RCC_PLLSOURCE_HSE;o.PLL.PLLM=4;o.PLL.PLLN=400;
    o.PLL.PLLP=2;o.PLL.PLLQ=8;o.PLL.PLLR=2;o.PLL.PLLRGE=RCC_PLL1VCIRANGE_1;o.PLL.PLLVCOSEL=RCC_PLL1VCOWIDE;o.PLL.PLLFRACN=0;
    check(HAL_RCC_OscConfig(&o));
    c.ClockType=RCC_CLOCKTYPE_SYSCLK|RCC_CLOCKTYPE_HCLK|RCC_CLOCKTYPE_D1PCLK1|RCC_CLOCKTYPE_PCLK1|RCC_CLOCKTYPE_PCLK2|RCC_CLOCKTYPE_D3PCLK1;
    c.SYSCLKSource=fast?RCC_SYSCLKSOURCE_PLLCLK:RCC_SYSCLKSOURCE_HSI;c.SYSCLKDivider=RCC_SYSCLK_DIV1;
    c.AHBCLKDivider=RCC_HCLK_DIV2;c.APB3CLKDivider=RCC_APB3_DIV2;c.APB1CLKDivider=RCC_APB1_DIV2;c.APB2CLKDivider=RCC_APB2_DIV2;c.APB4CLKDivider=RCC_APB4_DIV2;
    check(HAL_RCC_ClockConfig(&c,fast?FLASH_LATENCY_4:FLASH_LATENCY_1));
}
void board_init(void) {
    HAL_Init();
    MPU_Region_InitTypeDef m={0};HAL_MPU_Disable();m.Enable=MPU_REGION_ENABLE;m.Number=MPU_REGION_NUMBER0;m.BaseAddress=0x30000000;m.Size=MPU_REGION_SIZE_32KB;
    m.AccessPermission=MPU_REGION_FULL_ACCESS;m.DisableExec=MPU_INSTRUCTION_ACCESS_DISABLE;m.IsShareable=MPU_ACCESS_SHAREABLE;m.IsCacheable=MPU_ACCESS_NOT_CACHEABLE;m.IsBufferable=MPU_ACCESS_NOT_BUFFERABLE;
    HAL_MPU_ConfigRegion(&m);HAL_MPU_Enable(MPU_PRIVILEGED_DEFAULT);SCB_EnableICache();SCB_EnableDCache();
    __HAL_RCC_GPIOA_CLK_ENABLE();__HAL_RCC_GPIOB_CLK_ENABLE();__HAL_RCC_GPIOC_CLK_ENABLE();__HAL_RCC_GPIOD_CLK_ENABLE();__HAL_RCC_GPIOE_CLK_ENABLE();
    pin(GPIOC,GPIO_PIN_6,GPIO_MODE_OUTPUT_PP,0);HAL_GPIO_WritePin(GPIOC,GPIO_PIN_6,GPIO_PIN_RESET);
    pin(GPIOB,GPIO_PIN_0,GPIO_MODE_OUTPUT_PP,0);pin(GPIOD,GPIO_PIN_8|GPIO_PIN_9|GPIO_PIN_10|GPIO_PIN_11,GPIO_MODE_INPUT,0);
    cpu_clock(false);
    RCC_PeriphCLKInitTypeDef clk={0};clk.PeriphClockSelection=RCC_PERIPHCLK_USB|RCC_PERIPHCLK_I2C1|RCC_PERIPHCLK_ADC;
    clk.UsbClockSelection=RCC_USBCLKSOURCE_HSI48;clk.I2c123ClockSelection=RCC_I2C123CLKSOURCE_HSI;clk.AdcClockSelection=RCC_ADCCLKSOURCE_CLKP;
    check(HAL_RCCEx_PeriphCLKConfig(&clk));
    __HAL_RCC_CRS_CLK_ENABLE();
    RCC_CRSInitTypeDef crs={0};crs.Prescaler=RCC_CRS_SYNC_DIV1;crs.Source=RCC_CRS_SYNC_SOURCE_USB2;
    crs.Polarity=RCC_CRS_SYNC_POLARITY_RISING;crs.ReloadValue=47999;crs.ErrorLimitValue=34;crs.HSI48CalibrationValue=32;
    HAL_RCCEx_CRSConfig(&crs);
    __HAL_RCC_USB2_OTG_FS_CLK_ENABLE();HAL_PWREx_EnableUSBVoltageDetector();
    pin(GPIOA,GPIO_PIN_11|GPIO_PIN_12,GPIO_MODE_AF_PP,GPIO_AF10_OTG2_HS);
    pin(GPIOA,GPIO_PIN_9,GPIO_MODE_INPUT,0);USB_OTG_FS->GCCFG|=USB_OTG_GCCFG_VBDEN;
    HAL_NVIC_SetPriority(OTG_FS_IRQn,5,0);HAL_NVIC_EnableIRQ(OTG_FS_IRQn);
    pin(GPIOB,GPIO_PIN_8|GPIO_PIN_9,GPIO_MODE_AF_OD,GPIO_AF4_I2C1);__HAL_RCC_I2C1_CLK_ENABLE();
    oled_i2c.Instance=I2C1;oled_i2c.Init.Timing=0x00702991; /* 400 kHz target at HSI64; validate rise/fall times */
    oled_i2c.Init.AddressingMode=I2C_ADDRESSINGMODE_7BIT;oled_i2c.Init.NoStretchMode=I2C_NOSTRETCH_DISABLE;check(HAL_I2C_Init(&oled_i2c));
    check(HAL_I2CEx_ConfigAnalogFilter(&oled_i2c,I2C_ANALOGFILTER_ENABLE));
    HAL_NVIC_SetPriority(I2C1_EV_IRQn,9,0);HAL_NVIC_EnableIRQ(I2C1_EV_IRQn);HAL_NVIC_SetPriority(I2C1_ER_IRQn,9,0);HAL_NVIC_EnableIRQ(I2C1_ER_IRQn);
    __HAL_RCC_ADC12_CLK_ENABLE();pin(GPIOC,GPIO_PIN_0|GPIO_PIN_1,GPIO_MODE_ANALOG,0);
    adc.Instance=ADC1;adc.Init.ClockPrescaler=ADC_CLOCK_ASYNC_DIV4;adc.Init.Resolution=ADC_RESOLUTION_16B;
    adc.Init.ScanConvMode=ADC_SCAN_DISABLE;adc.Init.EOCSelection=ADC_EOC_SINGLE_CONV;adc.Init.NbrOfConversion=1;adc.Init.ExternalTrigConv=ADC_SOFTWARE_START;
    adc.Init.ConversionDataManagement=ADC_CONVERSIONDATA_DR;adc.Init.Overrun=ADC_OVR_DATA_OVERWRITTEN;check(HAL_ADC_Init(&adc));
    check(HAL_ADCEx_Calibration_Start(&adc,ADC_CALIB_OFFSET,ADC_SINGLE_ENDED));
    CoreDebug->DEMCR|=CoreDebug_DEMCR_TRCENA_Msk;DWT->CYCCNT=0;DWT->CTRL|=DWT_CTRL_CYCCNTENA_Msk;
}
bool board_power_available(void) {
    /* A configured USB2 host allows the declared 500mA. Type-C Rp >=1.5A
       permits standalone operation. Default-current sources need enumeration. */
    if(tud_mounted() && !tud_suspended())return true;
    for(unsigned ch=0;ch<2;ch++) {
        ADC_ChannelConfTypeDef c={0};c.Channel=ch?ADC_CHANNEL_11:ADC_CHANNEL_10;c.Rank=ADC_REGULAR_RANK_1;c.SamplingTime=ADC_SAMPLETIME_64CYCLES_5;c.SingleDiff=ADC_SINGLE_ENDED;
        if(HAL_ADC_ConfigChannel(&adc,&c)!=HAL_OK)return false;
        HAL_ADC_Start(&adc);
        if(HAL_ADC_PollForConversion(&adc,2)==HAL_OK) {
            uint32_t value=HAL_ADC_GetValue(&adc);HAL_ADC_Stop(&adc);
            if(value>13107)return true; /* >0.66V with 3.3V reference */
        } else HAL_ADC_Stop(&adc);
    }
    return false;
}
static void dma_init(DMA_HandleTypeDef *d,DMA_Stream_TypeDef *stream,uint32_t req,uint32_t dir) {
    d->Instance=stream;d->Init.Request=req;d->Init.Direction=dir;d->Init.PeriphInc=DMA_PINC_DISABLE;d->Init.MemInc=DMA_MINC_ENABLE;
    d->Init.PeriphDataAlignment=DMA_PDATAALIGN_WORD;d->Init.MemDataAlignment=DMA_MDATAALIGN_WORD;
    d->Init.Mode=DMA_CIRCULAR;d->Init.Priority=DMA_PRIORITY_VERY_HIGH;d->Init.FIFOMode=DMA_FIFOMODE_DISABLE;check(HAL_DMA_Init(d));
}
void board_audio_start(void) {
    if(running)return;
    cpu_clock(true);
    RCC_PeriphCLKInitTypeDef c={0};c.PeriphClockSelection=RCC_PERIPHCLK_SAI1;c.Sai1ClockSelection=RCC_SAI1CLKSOURCE_PLL3;
    c.PLL3.PLL3M=8;c.PLL3.PLL3N=393;c.PLL3.PLL3P=8;c.PLL3.PLL3Q=8;c.PLL3.PLL3R=8;c.PLL3.PLL3RGE=RCC_PLL3VCIRANGE_0;c.PLL3.PLL3VCOSEL=RCC_PLL3VCOMEDIUM;c.PLL3.PLL3FRACN=1770;
    check(HAL_RCCEx_PeriphCLKConfig(&c));__HAL_RCC_SAI1_CLK_ENABLE();__HAL_RCC_DMA1_CLK_ENABLE();__HAL_RCC_D2SRAM1_CLK_ENABLE();
    pin(GPIOE,GPIO_PIN_2|GPIO_PIN_3|GPIO_PIN_4|GPIO_PIN_5|GPIO_PIN_6,GPIO_MODE_AF_PP,GPIO_AF6_SAI1);
    sai_tx.Instance=SAI1_Block_A;sai_tx.Init.AudioMode=SAI_MODEMASTER_TX;sai_tx.Init.Synchro=SAI_ASYNCHRONOUS;sai_tx.Init.OutputDrive=SAI_OUTPUTDRIVE_ENABLE;
    sai_tx.Init.NoDivider=SAI_MASTERDIVIDER_ENABLE;sai_tx.Init.FIFOThreshold=SAI_FIFOTHRESHOLD_1QF;sai_tx.Init.AudioFrequency=SAI_AUDIO_FREQUENCY_48K;
    sai_tx.Init.SynchroExt=SAI_SYNCEXT_DISABLE;sai_tx.Init.MonoStereoMode=SAI_STEREOMODE;sai_tx.Init.CompandingMode=SAI_NOCOMPANDING;sai_tx.Init.TriState=SAI_OUTPUT_NOTRELEASED;
    check(HAL_SAI_InitProtocol(&sai_tx,SAI_I2S_STANDARD,SAI_PROTOCOL_DATASIZE_24BIT,2));
    sai_rx.Instance=SAI1_Block_B;sai_rx.Init=sai_tx.Init;sai_rx.Init.AudioMode=SAI_MODESLAVE_RX;sai_rx.Init.Synchro=SAI_SYNCHRONOUS;sai_rx.Init.OutputDrive=SAI_OUTPUTDRIVE_DISABLE;
    check(HAL_SAI_InitProtocol(&sai_rx,SAI_I2S_STANDARD,SAI_PROTOCOL_DATASIZE_24BIT,2));
    dma_init(&dma_tx,DMA1_Stream0,DMA_REQUEST_SAI1_A,DMA_MEMORY_TO_PERIPH);__HAL_LINKDMA(&sai_tx,hdmatx,dma_tx);
    dma_init(&dma_rx,DMA1_Stream1,DMA_REQUEST_SAI1_B,DMA_PERIPH_TO_MEMORY);__HAL_LINKDMA(&sai_rx,hdmarx,dma_rx);
    HAL_NVIC_SetPriority(DMA1_Stream0_IRQn,3,0);HAL_NVIC_EnableIRQ(DMA1_Stream0_IRQn);HAL_NVIC_SetPriority(DMA1_Stream1_IRQn,3,0);HAL_NVIC_EnableIRQ(DMA1_Stream1_IRQn);
    memset(audio_tx,0,sizeof(audio_tx));memset(audio_rx,0,sizeof(audio_rx));audio_sequence=0;
    check(HAL_SAI_Receive_DMA(&sai_rx,(uint8_t *)audio_rx,DMA_WORDS));check(HAL_SAI_Transmit_DMA(&sai_tx,(uint8_t *)audio_tx,DMA_WORDS));
    /* MCLK/BCLK/LRCK must be valid before releasing codec reset. 50ms exceeds 2048/fs. */
    HAL_Delay(50);HAL_GPIO_WritePin(GPIOC,GPIO_PIN_6,GPIO_PIN_SET);running=true;
}
void board_audio_stop(void) {
    if(!running)return;
    HAL_GPIO_WritePin(GPIOC,GPIO_PIN_6,GPIO_PIN_RESET);HAL_SAI_DMAStop(&sai_tx);HAL_SAI_DMAStop(&sai_rx);running=false;cpu_clock(false);
}
bool board_audio_running(void){return running;}
void HAL_SAI_RxHalfCpltCallback(SAI_HandleTypeDef *s){(void)s;audio_sequence++;}
void HAL_SAI_RxCpltCallback(SAI_HandleTypeDef *s){(void)s;audio_sequence++;}
void HAL_SAI_ErrorCallback(SAI_HandleTypeDef *s){(void)s;audio_overruns++;HAL_GPIO_WritePin(GPIOC,GPIO_PIN_6,GPIO_PIN_RESET);}
void DMA1_Stream0_IRQHandler(void){HAL_DMA_IRQHandler(&dma_tx);}
void DMA1_Stream1_IRQHandler(void){HAL_DMA_IRQHandler(&dma_rx);}
void I2C1_EV_IRQHandler(void){HAL_I2C_EV_IRQHandler(&oled_i2c);}
void I2C1_ER_IRQHandler(void){HAL_I2C_ER_IRQHandler(&oled_i2c);}
void OTG_FS_IRQHandler(void){tusb_int_handler(0,true);}
void SysTick_Handler(void){HAL_IncTick();}
void HardFault_Handler(void){board_fatal();}
void MemManage_Handler(void){board_fatal();}
void BusFault_Handler(void){board_fatal();}
void UsageFault_Handler(void){board_fatal();}
