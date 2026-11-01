#ifndef VP_UI_H
#define VP_UI_H
#include "dsp.h"
void ui_init(void);
void ui_task(vp_dsp *d,unsigned *route,uint32_t underruns);
#endif
