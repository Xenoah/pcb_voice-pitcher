/* USB Audio Class 2.0: fixed 48kHz, stereo packed 24-bit, asynchronous duplex.
 * Descriptor macros and stack are supplied by TinyUSB (MIT license).
 * 0xCAFE is the TinyUSB example VID, for development only; provision a licensed
 * VID/PID before distributing a product.
 */
#include "tusb.h"
#include "board.h"
#include <string.h>
bool usb_playback,usb_capture;
static uint32_t feedback_previous;
static const tusb_desc_device_t device={
 .bLength=sizeof(tusb_desc_device_t),.bDescriptorType=TUSB_DESC_DEVICE,.bcdUSB=0x0200,
 .bDeviceClass=TUSB_CLASS_MISC,.bDeviceSubClass=MISC_SUBCLASS_COMMON,.bDeviceProtocol=MISC_PROTOCOL_IAD,
 .bMaxPacketSize0=64,.idVendor=0xCAFE,.idProduct=0x4014,.bcdDevice=0x0001,
 .iManufacturer=1,.iProduct=2,.iSerialNumber=3,.bNumConfigurations=1};
uint8_t const *tud_descriptor_device_cb(void){return (const uint8_t *)&device;}
#define AS(iface,terminal,ep,nend) \
 TUD_AUDIO_DESC_STD_AS_INT(iface,0,0,2), \
 TUD_AUDIO_DESC_STD_AS_INT(iface,1,nend,2), \
 TUD_AUDIO_DESC_CS_AS_INT(terminal,AUDIO_CTRL_NONE,AUDIO_FORMAT_TYPE_I,AUDIO_DATA_FORMAT_TYPE_I_PCM,2,3,0), \
 TUD_AUDIO_DESC_TYPE_I_FORMAT(3,24), \
 TUD_AUDIO_DESC_STD_AS_ISO_EP(ep,TUSB_XFER_ISOCHRONOUS|TUSB_ISO_EP_ATT_ASYNCHRONOUS|TUSB_ISO_EP_ATT_DATA,294,1), \
 TUD_AUDIO_DESC_CS_AS_ISO_EP(AUDIO_CS_AS_ISO_DATA_EP_ATT_NON_MAX_PACKETS_OK,AUDIO_CTRL_NONE,0,0)
static const uint8_t configuration[]={
 TUD_CONFIG_DESCRIPTOR(1,3,0,9+CFG_TUD_AUDIO_FUNC_1_DESC_LEN,0,500),
 TUD_AUDIO_DESC_IAD(0,3,2),TUD_AUDIO_DESC_STD_AC(0,0,2),
 TUD_AUDIO_DESC_CS_AC(0x0200,AUDIO_FUNC_PRO_AUDIO,8+17+12+17+12,0),
 TUD_AUDIO_DESC_CLK_SRC(4,1,5,0,0),
 TUD_AUDIO_DESC_INPUT_TERM(1,AUDIO_TERM_TYPE_USB_STREAMING,0,4,2,3,0,0,0),
 TUD_AUDIO_DESC_OUTPUT_TERM(3,0x0603,0,1,4,0,0),
 TUD_AUDIO_DESC_INPUT_TERM(0x11,0x0603,0,4,2,3,0,0,0),
 TUD_AUDIO_DESC_OUTPUT_TERM(0x13,AUDIO_TERM_TYPE_USB_STREAMING,0,0x11,4,0,0),
 AS(1,1,0x01,2),TUD_AUDIO_DESC_STD_AS_ISO_FB_EP(0x82,3,4),
 AS(2,0x13,0x81,1)
};
_Static_assert(sizeof(configuration)==9+CFG_TUD_AUDIO_FUNC_1_DESC_LEN,"UAC descriptor length");
uint8_t const *tud_descriptor_configuration_cb(uint8_t index){(void)index;return configuration;}
uint16_t const *tud_descriptor_string_cb(uint8_t index,uint16_t language) {
    (void)language;static uint16_t result[40];
    const char *text;char serial[25];
    if(index==0){result[0]=0x0304;result[1]=0x0409;return result;}
    if(index==1)text="Xenoah";
    else if(index==2)text="Voice Pitcher Prototype";
    else if(index==3) {
        const char hex[]="0123456789ABCDEF";uint32_t id[3]={HAL_GetUIDw0(),HAL_GetUIDw1(),HAL_GetUIDw2()};
        for(int n=0;n<24;n++)serial[n]=hex[(id[n/8]>>(28-4*(n%8)))&15];serial[24]=0;text=serial;
    }else return NULL;
    unsigned n=(unsigned)strlen(text);if(n>39)n=39;result[0]=(uint16_t)(0x0300|((n+1)*2));
    for(unsigned i=0;i<n;i++)result[i+1]=(uint8_t)text[i];return result;
}
bool tud_audio_get_req_entity_cb(uint8_t port,tusb_control_request_t const *request) {
    const audio_control_request_t *r=(const audio_control_request_t *)request;
    if(r->bEntityID!=4 || r->bChannelNumber)return false;
    if(r->bControlSelector==AUDIO_CS_CTRL_SAM_FREQ) {
        if(r->bRequest==AUDIO_CS_REQ_CUR){uint32_t rate=48000;return tud_audio_buffer_and_schedule_control_xfer(port,request,&rate,4);}
        if(r->bRequest==AUDIO_CS_REQ_RANGE){audio_control_range_4_n_t(1) range={.wNumSubRanges=1,.subrange={{48000,48000,0}}};return tud_audio_buffer_and_schedule_control_xfer(port,request,&range,sizeof(range));}
    }
    if(r->bControlSelector==AUDIO_CS_CTRL_CLK_VALID && r->bRequest==AUDIO_CS_REQ_CUR){uint8_t valid=board_audio_running();return tud_audio_buffer_and_schedule_control_xfer(port,request,&valid,1);}
    return false;
}
bool tud_audio_set_req_entity_cb(uint8_t port,tusb_control_request_t const *request,uint8_t *buffer) {
    (void)port;const audio_control_request_t *r=(const audio_control_request_t *)request;uint32_t rate=0;
    if(r->bEntityID!=4 || r->bControlSelector!=AUDIO_CS_CTRL_SAM_FREQ || r->bRequest!=AUDIO_CS_REQ_CUR || r->wLength!=4)return false;
    memcpy(&rate,buffer,4);return rate==48000;
}
bool tud_audio_set_itf_cb(uint8_t port,tusb_control_request_t const *request) {
    (void)port;unsigned itf=tu_le16toh(request->wIndex),alt=tu_le16toh(request->wValue);
    if(alt>1)return false;
    if(itf==1)usb_playback=alt!=0;else if(itf==2)usb_capture=alt!=0;else return false;
    feedback_previous=DWT->CYCCNT;return true;
}
bool tud_audio_set_itf_close_EP_cb(uint8_t port,tusb_control_request_t const *request){(void)port;(void)request;return true;}
void tud_audio_feedback_params_cb(uint8_t function,uint8_t alt,audio_feedback_params_t *p) {
    (void)function;(void)alt;p->method=AUDIO_FEEDBACK_METHOD_FREQUENCY_FIXED;p->sample_freq=48000;p->frequency.mclk_freq=SystemCoreClock;feedback_previous=DWT->CYCCNT;
}
void tud_audio_feedback_interval_isr(uint8_t function,uint32_t frame,uint8_t shift) {
    (void)frame;(void)shift;uint32_t now=DWT->CYCCNT,elapsed=now-feedback_previous;feedback_previous=now;
    if(board_audio_running())tud_audio_feedback_update(function,elapsed);
}
void tud_umount_cb(void){usb_playback=usb_capture=false;}
uint32_t tusb_time_millis_api(void){return HAL_GetTick();}
