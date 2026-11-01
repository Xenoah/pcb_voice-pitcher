#include "dsp.h"
#include <math.h>
#include <string.h>
#define PI 3.14159265358979323846f
static float clamp(float x,float lo,float hi) { return x<lo?lo:(x>hi?hi:x); }
static float sane(float x,float fallback) { return isfinite(x)?x:fallback; }

void vp_init(vp_dsp *d) {
    memset(d,0,sizeof(*d));d->ratio=1.0f;d->grain=d->grain_target=VP_GRAIN;
    d->params=(vp_parameters){VP_DRY,0,1,30,0xFFF,0.35f};
}
void vp_set(vp_dsp *d,const vp_parameters *p) {
    vp_parameters next=*p;
    if ((unsigned)next.mode>=VP_MODE_COUNT) next.mode=VP_DRY;
    next.semitones=clamp(sane(next.semitones,0),-12,12);
    next.wet=clamp(sane(next.wet,1),0,1);
    next.retune_ms=clamp(sane(next.retune_ms,30),1,500);
    next.feedback=clamp(sane(next.feedback,.35f),0,.85f);
    next.scale &= 0xFFF;if(!next.scale)next.scale=0xFFF;
    d->params=next;
}
float vp_nearest_note(float midi,uint16_t scale) {
    if (!isfinite(midi))return 69;
    if (!(scale&0xFFF))scale=0xFFF;
    int center=(int)floorf(midi),best=center;float error=100;
    for(int note=center-12;note<=center+12;note++) {
        int pc=((note%12)+12)%12;
        float e=fabsf(midi-note);
        if ((scale&(1u<<pc)) && e<error) {error=e;best=note;}
    }
    return (float)best;
}
static float yin_result(const float *diff,float rate,float *confidence) {
    *confidence=0;
    int lag=15;
    while(lag<171 && diff[lag]>.15f)lag++;
    if(lag>=171 || !isfinite(diff[lag]))return 0;
    while(lag<171 && diff[lag+1]<diff[lag])lag++;
    float denominator=diff[lag-1]-2*diff[lag]+diff[lag+1];
    float delta=fabsf(denominator)>1e-10f?.5f*(diff[lag-1]-diff[lag+1])/denominator:0;
    *confidence=clamp(1-diff[lag],0,1);
    return rate/(lag+clamp(delta,-.5f,.5f));
}
float vp_yin(const float *s,size_t length,float rate,float *confidence) {
    float diff[173]={0}, energy=0, running=0;
    *confidence=0;
    if(length<344 || rate!=12000)return 0;
    for(size_t i=0;i<length;i++)energy+=s[i]*s[i];
    if(energy/length<0.00003f)return 0;
    size_t count=length-172;
    for(int lag=1;lag<=172;lag++) {
        float sum=0;
        for(size_t i=0;i<count;i++){float e=s[i]-s[i+lag];sum+=e*e;}
        running+=sum;diff[lag]=running>1e-20f?sum*lag/running:1;
    }
    return yin_result(diff,rate,confidence);
}
static void analysis_step(vp_dsp *d,unsigned budget) {
    /* Bounded work per audio block. A 172-lag scan must not run in one DMA
       deadline; the snapshot remains unchanged until all lags are complete. */
    while(d->yin_lag && budget--) {
        unsigned lag=d->yin_lag;float sum=0;
        for(unsigned i=0;i<VP_YIN-172;i++){float e=d->yin[i]-d->yin[i+lag];sum+=e*e;}
        d->yin_sum+=sum;d->difference[lag]=d->yin_sum>1e-20f?sum*lag/d->yin_sum:1;
        if(++d->yin_lag>172) {
            d->yin_lag=0;d->frequency=yin_result(d->difference,12000,&d->confidence);d->correction=0;
            if(d->frequency>0 && d->confidence>.85f) {
                float note=69+12*log2f(d->frequency/440);
                d->correction=clamp(vp_nearest_note(note,d->params.scale)-note,-2,2);
                float period=VP_RATE/d->frequency;
                /* Half a grain must contain an integer number of periods. */
                d->grain_target=clamp(2*roundf(VP_GRAIN/(2*period))*period,512,3072);
            }
        }
    }
}
static float read_delay(vp_dsp *d,int ch,float delay) {
    float position=d->write-delay;
    while(position<0)position+=VP_RING;
    unsigned index=(unsigned)position;
    float t=position-index;
    return d->ring[ch][index&(VP_RING-1)]*(1-t)+d->ring[ch][(index+1)&(VP_RING-1)]*t;
}
void vp_process(vp_dsp *d,const float *in,float *out,size_t frames) {
    const float retune=1-expf(-1/(.001f*VP_RATE*d->params.retune_ms));
    for(size_t n=0;n<frames;n++) {
        float x[2]={sane(in[2*n],0),sane(in[2*n+1],0)};
        /* Detection uses left channel, avoiding cancellation of anti-phase stereo. */
        d->analysis_filter[0]+=.145f*(x[0]-d->analysis_filter[0]);
        d->analysis_filter[1]+=.145f*(d->analysis_filter[0]-d->analysis_filter[1]);
        if(++d->decimation==4) {
            d->decimation=0;
            d->analysis[d->analysis_write]=d->analysis_filter[1];
            d->analysis_write=(d->analysis_write+1)%VP_YIN;
            if(++d->analysis_hop>=128 && d->samples>=VP_YIN*4 && !d->yin_lag) {
                d->analysis_hop=0;
                float energy=0;
                for(unsigned i=0;i<VP_YIN;i++){d->yin[i]=d->analysis[(d->analysis_write+i)%VP_YIN];energy+=d->yin[i]*d->yin[i];}
                if(energy/VP_YIN>=.00003f){d->yin_lag=1;d->yin_sum=0;}
                else {d->frequency=d->confidence=d->correction=0;}
            }
        }
        float semitones=d->params.mode==VP_TUNE?d->correction:d->params.semitones;
        float target=(d->params.mode==VP_SHIFT||d->params.mode==VP_TUNE)?exp2f(semitones/12):1;
        d->ratio+=retune*(target-d->ratio);
        d->grain+=.0002f*(d->grain_target-d->grain);
        /* Four-pole low-pass reduces aliasing during upward transposition.
           This intentionally sacrifices upper bandwidth; it is not lossless. */
        float cutoff=18000/fmaxf(d->ratio,1);
        float aa=1-expf(-2*PI*cutoff/VP_RATE);
        for(int ch=0;ch<2;ch++) {
            float z=x[ch];
            for(int p=0;p<4;p++){d->anti_alias[ch][p]+=aa*(z-d->anti_alias[ch][p]);z=d->anti_alias[ch][p];}
            d->ring[ch][d->write]=d->ratio>1.001f?z:x[ch];
        }
        float phase2=d->phase+.5f;if(phase2>=1)phase2-=1;
        float weight=sinf(PI*d->phase);weight*=weight;
        float tremolo=.65f+.35f*sinf(2*PI*d->lfo_phase);
        for(int ch=0;ch<2;ch++) {
            float wet=x[ch];
            switch(d->params.mode) {
            case VP_SHIFT:case VP_TUNE:
                /* Identity is exact when requested explicitly in shift mode. */
                if(d->params.mode==VP_SHIFT && fabsf(d->params.semitones)<1e-7f)wet=x[ch];
                else wet=weight*read_delay(d,ch,64+d->phase*d->grain)+(1-weight)*read_delay(d,ch,64+phase2*d->grain);
                break;
            case VP_DELAY:
                wet=d->delay[ch][d->delay_write];
                d->delay[ch][d->delay_write]=clamp(x[ch]+wet*d->params.feedback,-1,1);
                wet=.65f*x[ch]+.35f*wet;break;
            case VP_TREMOLO:wet=x[ch]*tremolo;break;
            default:break;
            }
            float y=x[ch]+d->params.wet*(wet-x[ch]);
            if(fabsf(y)>1)d->clipped++;
            out[2*n+ch]=clamp(y,-1,1);
        }
        d->phase+=(1-d->ratio)/d->grain;
        if(d->phase<0)d->phase+=1;
        if(d->phase>=1)d->phase-=1;
        d->lfo_phase+=5.0f/VP_RATE;if(d->lfo_phase>=1)d->lfo_phase-=1;
        d->write=(d->write+1)&(VP_RING-1);d->delay_write=(d->delay_write+1)%VP_DELAY_SAMPLES;d->samples++;
    }
    analysis_step(d,(unsigned)((frames+3)/4));
}
int32_t vp_to_pcm24(float x) {
    x=clamp(sane(x,0),-1,8388607.0f/8388608.0f);
    return (int32_t)lrintf(x*8388608.0f);
}
float vp_from_pcm24(int32_t x) {return clamp((float)x/8388608.0f,-1,1);}
