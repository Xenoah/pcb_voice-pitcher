#ifndef VP_DSP_H
#define VP_DSP_H
#include <stddef.h>
#include <stdint.h>

enum vp_mode { VP_DRY, VP_SHIFT, VP_TUNE, VP_DELAY, VP_TREMOLO, VP_MODE_COUNT };
enum { VP_RATE=48000, VP_GRAIN=2048, VP_RING=4096, VP_DELAY_SAMPLES=24000, VP_YIN=512 };
typedef struct {
    enum vp_mode mode;
    float semitones;        /* -12 .. +12 */
    float wet;             /* 0 .. 1; pitch processing normally 1 */
    float retune_ms;        /* 1 .. 500 ms */
    uint16_t scale;         /* pitch-class bit mask, C=bit 0; 0xFFF=chromatic */
    float feedback;        /* delay feedback, 0 .. 0.85 */
} vp_parameters;
typedef struct {
    vp_parameters params;
    float ring[2][VP_RING], delay[2][VP_DELAY_SAMPLES];
    float analysis[VP_YIN], yin[VP_YIN], difference[173];
    float phase, lfo_phase, ratio, frequency, confidence, correction, grain, grain_target;
    float anti_alias[2][4], analysis_filter[2];
    uint32_t write, delay_write, analysis_write, samples, clipped;
    uint32_t decimation, analysis_hop;
    unsigned yin_lag;
    float yin_sum;
} vp_dsp;

void vp_init(vp_dsp *dsp);
void vp_set(vp_dsp *dsp, const vp_parameters *parameters);
void vp_process(vp_dsp *dsp, const float *stereo_in, float *stereo_out, size_t frames);
float vp_yin(const float *signal, size_t length, float rate, float *confidence);
float vp_nearest_note(float midi, uint16_t scale);
int32_t vp_to_pcm24(float value);
float vp_from_pcm24(int32_t value);
#endif
