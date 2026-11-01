#include "dsp.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static vp_dsp state;
int main(int argc,char **argv) {
    float signal[512],confidence=0;
    for(int k=0;k<7;k++) {
        float hz=(float[]){73.42f,110,196,220,440,659.25f,783.99f}[k];
        for(int i=0;i<512;i++) signal[i]=.4f*sinf(6.28318530718f*hz*i/12000)+.1f*sinf(12.56637061436f*hz*i/12000);
        float estimate=vp_yin(signal,512,12000,&confidence);
        float cents=1200*log2f(estimate/hz);
        assert(fabsf(cents)<12);assert(confidence>.9);
    }
    memset(signal,0,sizeof(signal));assert(vp_yin(signal,512,12000,&confidence)==0);
    assert(vp_nearest_note(61.1f,0xAB5)==62); /* C major */
    assert(vp_to_pcm24(1)==8388607);assert(vp_to_pcm24(-1)==-8388608);assert(vp_to_pcm24(NAN)==0);
    for(int32_t value=-8388608;value<8388607;value+=251)assert(vp_to_pcm24(vp_from_pcm24(value))==value);
    vp_init(&state);
    float in[64],out[64];for(int i=0;i<64;i++)in[i]=.8f*sinf(i*.17f);
    vp_process(&state,in,out,32);assert(memcmp(in,out,sizeof(in))==0);
    vp_parameters p=state.params;p.mode=VP_SHIFT;p.semitones=0;vp_set(&state,&p);
    vp_process(&state,in,out,32);assert(memcmp(in,out,sizeof(in))==0);
    p.mode=VP_TUNE;p.wet=NAN;p.retune_ms=0;p.feedback=1;p.scale=0;vp_set(&state,&p);
    for(int b=0;b<2000;b++){vp_process(&state,in,out,32);for(int i=0;i<64;i++)assert(isfinite(out[i])&&fabsf(out[i])<=1);}
    if(argc>=3) {
        vp_init(&state);p=state.params;p.mode=strcmp(argv[1],"tune")==0?VP_TUNE:VP_SHIFT;p.semitones=(float)atof(argv[1]);vp_set(&state,&p);
        float frequency=argc>3?(float)atof(argv[3]):440;
        FILE *f=fopen(argv[2],"wb");assert(f);
        for(int block=0;block<4500;block++) {
            for(int n=0;n<32;n++)in[2*n]=in[2*n+1]=.5f*sinf(6.28318530718f*frequency*(block*32+n)/48000);
            vp_process(&state,in,out,32);assert(fwrite(out,sizeof(float),64,f)==64);
        }
        fclose(f);
        printf("Final detection %.3f Hz, confidence %.4f, correction %.3f st\n",state.frequency,state.confidence,state.correction);
    }
    puts("DSP checks passed: pitch estimate, scale, silence, PCM bounds, dry identity, finite long-run output.");
    return 0;
}
