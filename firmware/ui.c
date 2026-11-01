#include "ui.h"
#include "board.h"
#include <math.h>
#include <stdio.h>
#include <string.h>
static uint8_t screen[1024],packet[129],command[4],page,phase;
static bool present;
static unsigned root,scale_type;
/* Original compact 5x7 glyphs: 0-9, A-Z, space, dash, dot, plus, slash. */
static const char alphabet[]="0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ -. +/";
static const uint8_t font[][5]={
 {62,81,73,69,62},{0,66,127,64,0},{98,81,73,73,70},{34,65,73,73,54},{24,20,18,127,16},
 {39,69,69,69,57},{60,74,73,73,48},{1,113,9,5,3},{54,73,73,73,54},{6,73,73,41,30},
 {126,17,17,17,126},{127,73,73,73,54},{62,65,65,65,34},{127,65,65,34,28},{127,73,73,73,65},
 {127,9,9,9,1},{62,65,73,73,122},{127,8,8,8,127},{0,65,127,65,0},{32,64,65,63,1},
 {127,8,20,34,65},{127,64,64,64,64},{127,2,12,2,127},{127,4,8,16,127},{62,65,65,65,62},
 {127,9,9,9,6},{62,65,81,33,94},{127,9,25,41,70},{38,73,73,73,50},{1,1,127,1,1},
 {63,64,64,64,63},{31,32,64,32,31},{63,64,56,64,63},{99,20,8,20,99},{7,8,112,8,7},{97,81,73,69,67},
 {0,0,0,0,0},{8,8,8,8,8},{0,96,96,0,0},{0,0,0,0,0},{8,8,62,8,8},{32,16,8,4,2}
};
static void line(unsigned row,const char *text) {
    unsigned x=0;
    for(;*text&&x<123;text++,x+=6){const char *g=strchr(alphabet,*text);if(g)memcpy(&screen[row*128+x],font[g-alphabet],5);}
}
void ui_init(void) {
    uint8_t init[]={0x00,0xAE,0xD5,0x80,0xA8,0x3F,0xD3,0,0x40,0x8D,0x14,0x20,2,0xA1,0xC8,0xDA,0x12,0x81,0x7F,0xD9,0xF1,0xDB,0x40,0xA4,0xA6,0xAF};
    present=HAL_I2C_IsDeviceReady(&oled_i2c,0x3C<<1,2,10)==HAL_OK;
    if(present)present=HAL_I2C_Master_Transmit(&oled_i2c,0x3C<<1,init,sizeof(init),20)==HAL_OK;
}
static void button(vp_dsp *d,unsigned *route,unsigned key,bool long_press) {
    vp_parameters p=d->params;
    if(key==0) {
        if(long_press)scale_type=(scale_type+1)%3;
        else p.mode=(p.mode+1)%VP_MODE_COUNT;
    } else if(key==3)*route=(*route+1)%4;
    else {
        int direction=key==1?-1:1;
        if(p.mode==VP_TUNE)root=(root+12+direction)%12;
        else if(p.mode==VP_DELAY)p.feedback+=direction*.05f;
        else if(p.mode==VP_TREMOLO)p.wet+=direction*.1f;
        else p.semitones+=direction;
    }
    uint16_t scale=scale_type==1?0xAB5:(scale_type==2?0x5AD:0xFFF);
    p.scale=(uint16_t)(((scale<<root)|(scale>>(12-root)))&0xFFF);vp_set(d,&p);
}
void ui_task(vp_dsp *d,unsigned *route,uint32_t underruns) {
    static uint32_t changed[4],pressed[4],last_render;static bool raw[4],stable[4];
    uint32_t now=HAL_GetTick();
    for(unsigned k=0;k<4;k++) {
        bool value=(GPIOD->IDR&(GPIO_PIN_8<<k))==0;
        if(value!=raw[k]){raw[k]=value;changed[k]=now;}
        if(value!=stable[k] && now-changed[k]>=20) {
            stable[k]=value;
            if(value){pressed[k]=now;if(k==1||k==2)button(d,route,k,false);}
            else if(k==0||k==3)button(d,route,k,now-pressed[k]>=600);
        }
    }
    if(!present)return;
    if(now-last_render>=100) {
        last_render=now;memset(screen,0,sizeof(screen));char s[32];
        const char *modes[]={"DRY","PITCH SHIFT","AUTO TUNE","DELAY","TREMOLO"};
        line(0,"VOICE PITCHER");line(1,modes[d->params.mode]);
        snprintf(s,sizeof(s),"SHIFT %+d ST",(int)d->params.semitones);line(2,s);
        if(d->frequency>0){snprintf(s,sizeof(s),"PITCH %u HZ",(unsigned)(d->frequency+.5f));line(3,s);
            float note=69+12*log2f(d->frequency/440);int cents=(int)lrintf(100*(note-roundf(note)));
            snprintf(s,sizeof(s),"MIDI %d  %+d CENTS",(int)lrintf(note),cents);line(4,s);
        }else line(3,"PITCH --");
        const char *routes[]={"LINE / LINE","LINE / USB","USB / LINE","USB / USB"};line(5,routes[*route]);
        snprintf(s,sizeof(s),"KEY %s %s",(const char *[]){"C","DB","D","EB","E","F","GB","G","AB","A","BB","B"}[root],(const char *[]){"CHROM","MAJOR","MINOR"}[scale_type]);line(6,s);
        if(!board_audio_running())line(7,"WAIT USB POWER");
        else if(underruns||audio_overruns)line(7,"AUDIO UNDERRUN");
        else if(d->clipped)line(7,"CLIP - REDUCE INPUT");
        else line(7,"48K 24BIT PROTOTYPE");
    }
    /* Page writes are interrupt-driven: no 1024-byte blocking display transfer. */
    if(HAL_I2C_GetState(&oled_i2c)!=HAL_I2C_STATE_READY)return;
    if(phase==0) {
        command[0]=0;command[1]=(uint8_t)(0xB0+page);command[2]=0;command[3]=0x10;
        if(HAL_I2C_Master_Transmit_IT(&oled_i2c,0x3C<<1,command,4)==HAL_OK)phase=1;
    } else {
        packet[0]=0x40;memcpy(packet+1,screen+128*page,128);
        if(HAL_I2C_Master_Transmit_IT(&oled_i2c,0x3C<<1,packet,129)==HAL_OK){phase=0;page=(page+1)&7;}
    }
}
