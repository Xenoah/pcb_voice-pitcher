#include "board.h"
#include "dsp.h"
#include "ui.h"
#include "tusb.h"
#include <string.h>
static vp_dsp dsp;
/* Inspect through SWD during bring-up. One 32-frame deadline is ~266667
   CPU cycles at 400MHz. This measures service time, not converter latency. */
volatile uint32_t app_audio_max_cycles;
extern bool usb_playback,usb_capture;
static int32_t sign24(uint32_t value){value&=0xFFFFFF;return (int32_t)(value&0x800000?value|0xFF000000:value);}
int main(void) {
    board_init();vp_init(&dsp);ui_init();
    tusb_rhport_init_t init={.role=TUSB_ROLE_DEVICE,.speed=TUSB_SPEED_FULL};tusb_init(0,&init);
    unsigned route=0;uint32_t processed=0,underruns=0,power_check=0;
    float input[64],output[64];uint8_t usb[192];
    for(;;) {
        tud_task();
        uint32_t now=HAL_GetTick();
        if(now-power_check>=100) {
            power_check=now;
            if(board_power_available()) {
                if(!board_audio_running()){board_audio_start();processed=audio_sequence;}
            }else if(board_audio_running())board_audio_stop();
        }
        uint32_t sequence=audio_sequence;
        if(board_audio_running() && sequence!=processed) {
            uint32_t cycle_start=DWT->CYCCNT;
            if(sequence-processed>1){underruns+=sequence-processed-1;}
            unsigned half=(sequence-1)&1,offset=half*64;
            bool source_usb=route>=2,target_usb=(route&1)!=0;
            unsigned bytes=0;
            /* Drain playback even when line input is selected, so changing
               routes cannot replay stale audio from a full USB FIFO. */
            if(usb_playback)bytes=tud_audio_read(usb,sizeof(usb));
            for(unsigned i=0;i<64;i++) {
                int32_t sample=0;
                if(!source_usb)sample=sign24((uint32_t)audio_rx[offset+i]);
                else if(3*i+2<bytes)sample=sign24((uint32_t)usb[3*i]|((uint32_t)usb[3*i+1]<<8)|((uint32_t)usb[3*i+2]<<16));
                input[i]=vp_from_pcm24(sample);
            }
            if(source_usb&&usb_playback&&bytes!=sizeof(usb))underruns++;
            vp_process(&dsp,input,output,32);
            for(unsigned i=0;i<64;i++) {
                uint32_t sample=(uint32_t)vp_to_pcm24(output[i]);
                audio_tx[offset+i]=target_usb?0:(int32_t)(sample&0xFFFFFF);
                usb[3*i]=(uint8_t)sample;usb[3*i+1]=(uint8_t)(sample>>8);usb[3*i+2]=(uint8_t)(sample>>16);
            }
            if(target_usb&&usb_capture&&tud_audio_write(usb,sizeof(usb))!=sizeof(usb))underruns++;
            if(!target_usb&&usb_capture){memset(usb,0,sizeof(usb));(void)tud_audio_write(usb,sizeof(usb));}
            if(audio_sequence!=sequence)underruns++; /* deadline miss is visible */
            uint32_t used=DWT->CYCCNT-cycle_start;
            if(used>app_audio_max_cycles)app_audio_max_cycles=used;
            processed=sequence;
        }
        ui_task(&dsp,&route,underruns);
        HAL_GPIO_WritePin(GPIOB,GPIO_PIN_0,(now/500)&1?GPIO_PIN_SET:GPIO_PIN_RESET);
    }
}
void _init(void){}
void _fini(void){}
