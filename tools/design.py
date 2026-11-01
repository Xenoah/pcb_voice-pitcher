"""Electrical design and placement source. All dimensions are millimetres.

PCB coordinates have origin at the lower left edge in generated CPL files.
Pin numbers are physical package pins, not MCU logical GPIO numbers.
"""
PARTS = []

def add(ref, value, symbol, footprint, pins, xy, page, mpn='', lcsc='', assembly='SMT', rotation=0):
    item = dict(ref=ref, value=value, symbol=symbol, footprint=footprint,
                pins={str(k):v for k,v in pins.items()}, x=xy[0], y=xy[1],
                rotation=rotation, page=page, mpn=mpn or value, lcsc=lcsc, assembly=assembly)
    PARTS.append(item)
    return item

RFP='Resistor_SMD:R_0603_1608Metric'
CFP='Capacitor_SMD:C_0603_1608Metric'
def r(ref,value,a,b,xy,page='power',rotation=0,lcsc=''):
    return add(ref,value,'Device:R',RFP,{1:a,2:b},xy,page,lcsc=lcsc,rotation=rotation)
def c(ref,value,a,b,xy,page='power',rotation=0,fp=CFP):
    return add(ref,value,'Device:C',fp,{1:a,2:b},xy,page,rotation=rotation)
def cp(ref,value,a,b,xy,page='analog'):
    return add(ref,value,'Device:C_Polarized','Capacitor_SMD:CP_Elec_4x5.8',
               {1:a,2:b},xy,page,mpn='UWT1C'+('4R7MCL1GB' if value=='4.7u' else '100MCL1GB'))

# USB2 device, both connector orientations. CC1/CC2 have separate Rd.
usb={p:'VBUS' for p in ['A4','A9','B4','B9']}
usb.update({p:'GND' for p in ['A1','A12','B1','B12','S1']})
usb.update({'A5':'CC1','B5':'CC2','A6':'USB_DP','B6':'USB_DP','A7':'USB_DM','B7':'USB_DM'})
add('J1','USB-C USB2 DEVICE','Connector:USB_C_Receptacle_USB2.0_16P',
    'Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12',usb,(133,53.5),'usb',mpn='TYPE-C-31-M-12',lcsc='C165948',rotation=180)
r('R1','5.1k','CC1','GND',(124,58),'usb')
r('R2','5.1k','CC2','GND',(124,61),'usb')
r('R3','1k','CC1','CC1_SENSE',(119,58),'usb')
r('R4','1k','CC2','CC2_SENSE',(119,61),'usb')
add('U3','USBLC6-2SC6','Power_Protection:USBLC6-2SC6','Package_TO_SOT_SMD:SOT-23-6',
    {1:'USB_DM',6:'USB_DM',3:'USB_DP',4:'USB_DP',2:'GND',5:'VBUS'},(133,61),'usb',lcsc='C7519')
c('C1','100n','VBUS','GND',(138,61),'usb')
r('R5','22','USB_DM','MCU_USB_DM',(121,91),'usb',rotation=90)
r('R6','22','USB_DP','MCU_USB_DP',(123,91),'usb',rotation=90)
# VBUS detect divider stays below 3.3V even with maximum USB supply voltage.
r('R7','100k','VBUS','VBUS_SENSE',(128,75),'usb')
r('R8','100k','VBUS_SENSE','GND',(132,75),'usb')
add('F1','500mA PTC','Device:Polyfuse','Fuse:Fuse_1206_3216Metric',
    {1:'VBUS',2:'+5V_RAW'},(138,66),'power',mpn='1206L050YR')
add('U7','TPS22918DBVR','VoicePitcher:TPS22918','Package_TO_SOT_SMD:SOT-23-6',
    {1:'+5V_RAW',2:'GND',3:'+5V_RAW',4:'SLEW_CT',6:'+5V'},(137,71),'power')
c('C47','1u','+5V_RAW','GND',(142,70),'power')
c('C48','10n','SLEW_CT','GND',(132,70),'power')
add('FB1','120R@100MHz','Device:FerriteBead','Inductor_SMD:L_0805_2012Metric',
    {1:'+5V',2:'+5VA'},(90,78),'power',mpn='BLM21PG121SN1D')
# 1117 output stability requires an electrolytic capacitor with suitable ESR.
add('U4','LD1117S33TR','Regulator_Linear:LD1117S33TR_SOT223','Package_TO_SOT_SMD:SOT-223-3_TabPin2',
    {1:'GND',2:'+3V3',3:'+5V'},(132,82),'power',mpn='LD1117S33TR')
cp('C2','10u','+5V','GND',(140,77),'power')
cp('C3','10u','+3V3','GND',(132,91),'power')
c('C4','100n','+3V3','GND',(126,81),'power')
cp('C5','10u','+5VA','GND',(85,78),'power')
c('C6','100n','+5VA','GND',(81,78),'power')

mcu={p:'+3V3' for p in [6,11,27,50,75,100]}
mcu.update({p:'GND' for p in [10,19,26,49,74,99]})
mcu.update({20:'+3V3A',21:'+3V3A',14:'NRST',94:'BOOT0',12:'HSE_8M',
 48:'VCAP1',73:'VCAP2',1:'SAI_MCLK',2:'SAI_ADC',3:'SAI_LRCK',4:'SAI_BCLK',5:'SAI_DAC',
 63:'CODEC_RESET',70:'MCU_USB_DM',71:'MCU_USB_DP',68:'VBUS_SENSE',
 15:'CC1_SENSE',16:'CC2_SENSE',72:'SWDIO',76:'SWCLK',89:'SWO',
 95:'I2C_SCL',96:'I2C_SDA',55:'KEY_MODE',56:'KEY_DOWN',57:'KEY_UP',58:'KEY_IO',
 46:'UART_TX',47:'UART_RX',34:'STATUS_LED'})
add('U1','STM32H743VIT6','MCU_ST_STM32H7:STM32H743VITx','Package_QFP:LQFP-100_14x14mm_P0.5mm',
    mcu,(107,103),'mcu',lcsc='C114409')
add('FB2','120R@100MHz','Device:FerriteBead','Inductor_SMD:L_0805_2012Metric',
    {1:'+3V3',2:'+3V3A'},(92,108),'mcu',mpn='BLM21PG121SN1D')
for ref,xy in [('C7',(96,96)),('C8',(96,110)),('C9',(108,114)),('C10',(118,100)),('C11',(107,92))]:
    c(ref,'100n','+3V3','GND',xy,'mcu')
c('C12','100n','+3V3A','GND',(91,111),'mcu')
c('C13','1u','+3V3A','GND',(91,114),'mcu')
c('C14','2.2u','VCAP1','GND',(114,114),'mcu')
c('C15','2.2u','VCAP2','GND',(118,97),'mcu')
c('C16','4.7u','+3V3','GND',(109,118),'mcu')
add('Y1','8MHz 3V3 CMOS','Oscillator:ASE-xxxMHz',
    'Oscillator:Oscillator_SMD_Abracon_ASE-4Pin_3.2x2.5mm',
    {1:'+3V3',2:'GND',3:'OSC_8M',4:'+3V3'},(91,98),'mcu',mpn='ASE-8.000MHZ-LC-T')
r('R9','33','OSC_8M','HSE_8M',(94,101),'mcu',rotation=90)
c('C17','100n','+3V3','GND',(87,98),'mcu')
r('R10','10k','+3V3','NRST',(124,116),'mcu')
c('C18','100n','NRST','GND',(124,119),'mcu')
r('R11','10k','BOOT0','GND',(130,116),'mcu')
for ref,net,xy in [('SW1','NRST',(122,125)),('SW2','BOOT0',(133,125))]:
    add(ref,'RESET' if ref=='SW1' else 'BOOT','Switch:SW_Push',
        'Button_Switch_SMD:SW_SPST_TL3342',{1:net,2:'GND' if ref=='SW1' else '+3V3'},xy,'mcu',mpn='TL3342F160QG')
add('J5','SWD','Connector_Generic:Conn_01x06',
    'Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical',
    {1:'+3V3',2:'SWDIO',3:'SWCLK',4:'GND',5:'NRST',6:'SWO'},(142,101),'mcu',mpn='1x6 2.54mm header',assembly='HAND')
add('J6','UART 3V3','Connector_Generic:Conn_01x03',
    'Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical',
    {1:'GND',2:'UART_TX',3:'UART_RX'},(142,122),'mcu',mpn='1x3 2.54mm header',assembly='HAND')

# PCM3060 hardware mode: slave ADC/DAC, I2S24, single ended outputs.
add('U2','PCM3060PWR','Audio:PCM3060','Package_SO:TSSOP-28_4.4x9.7mm_P0.65mm',
    {1:'GND',2:'GND',3:'SAI_ADC',4:'I2S_LRCK',5:'I2S_BCLK',6:'I2S_MCLK',7:'+3V3',8:'GND',
     9:'I2S_MCLK',10:'I2S_BCLK',11:'I2S_LRCK',12:'I2S_DAC',15:'CODEC_RESET',16:'GND',
     18:'DAC_R',20:'DAC_L',21:'VCOM',22:'GND',23:'GND',24:'+5VA',25:'ADC_L',26:'ADC_R',27:'GND',28:'CODEC_MODE'},
    (78,103),'codec',lcsc='C2651841')
r('R12','220k','+3V3','CODEC_MODE',(79,94),'codec')
r('R13','10k','CODEC_RESET','GND',(84,111),'codec')
for ref,src,dst,xy in [('R14','SAI_MCLK','I2S_MCLK',(97,91)),('R15','SAI_LRCK','I2S_LRCK',(97,87)),
                       ('R16','SAI_BCLK','I2S_BCLK',(101,87)),('R17','SAI_DAC','I2S_DAC',(101,91))]:
    r(ref,'33',src,dst,xy,'codec')
c('C19','100n','+3V3','GND',(73,104),'codec',rotation=90)
c('C20','100n','+5VA','GND',(83,100),'codec',rotation=90)
cp('C21','10u','VCOM','GND',(85,105),'codec')
c('C22','100n','VCOM','GND',(85,109),'codec')

# Physical jack pin mapping: CUI 1=sleeve, 2=tip, 3=ring. Symbol uses S/T/R.
for ref,net,xy in [('J2','IN',(59,89)),('J3','OUT',(59,116))]:
    add(ref,'3.5mm STEREO '+net,'Connector_Audio:AudioJack3',
        'Connector_Audio:Jack_3.5mm_CUI_SJ-3523-SMT_Horizontal',
        {'S':'GND','T':net+'_L','R':net+'_R'},xy,'analog',mpn='SJ-3523-SMT-TR',rotation=90)
    PARTS[-1]['pad_map']={'1':'S','2':'T','3':'R'}
add('U5','TLV9062IDR','Amplifier_Operational:TLV9062','Package_SO:SOIC-8_3.9x4.9mm_P1.27mm',
    {1:'BUF_L',2:'BUF_L',3:'BIAS_L',4:'GND',5:'BIAS_R',6:'BUF_R',7:'BUF_R',8:'+5VA'},
    (71,89),'analog')
c('C23','100n','+5VA','GND',(75,84),'analog')
for ch,dy,base in [('L',0,20),('R',8,25)]:
    y=77+dy
    r('R'+str(base),'10k','IN_'+ch,'ATT_'+ch,(64,y),'analog')
    r('R'+str(base+1),'10k','ATT_'+ch,'GND',(68,y),'analog')
    c('C'+str(base+4),'470p','ATT_'+ch,'GND',(64,y+3),'analog')
    cp('C'+str(base+5),'4.7u','BIAS_'+ch,'ATT_'+ch,(69,y+3),'analog')
    r('R'+str(base+2),'100k','BIAS_'+ch,'VCOM',(74,y),'analog')
    r('R'+str(base+3),'100','BUF_'+ch,'ADC_'+ch,(70,96+dy),'analog')
    c('C'+str(base+6),'2.2n','ADC_'+ch,'GND',(70,99+dy),'analog')
add('U6','TLV9062IDR','Amplifier_Operational:TLV9062','Package_SO:SOIC-8_3.9x4.9mm_P1.27mm',
    {1:'OBUF_L',2:'OBUF_L',3:'LPF_L',4:'GND',5:'LPF_R',6:'OBUF_R',7:'OBUF_R',8:'+5VA'},
    (75,121),'analog')
c('C34','100n','+5VA','GND',(81,118),'analog')
for ch,dx,base in [('L',0,30),('R',9,35)]:
    x=65+dx
    r('R'+str(base),'3.3k','DAC_'+ch,'LPF_'+ch,(x,112),'analog')
    c('C'+str(base+5),'1n','LPF_'+ch,'GND',(x,115),'analog')
    r('R'+str(base+1),'100','OBUF_'+ch,'COUPLE_'+ch,(x,125),'analog')
    cp('C'+str(base+6),'10u','COUPLE_'+ch,'OUT_'+ch,(x,130),'analog')
    r('R'+str(base+2),'100k','OUT_'+ch,'GND',(x,135),'analog')

# SSD1306 module: 4-pin 3.3V I2C type. Verify order; modules are not interchangeable.
add('J4','OLED GND VCC SCL SDA','Connector_Generic:Conn_01x04',
    'Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical',
    {1:'GND',2:'+3V3',3:'I2C_SCL',4:'I2C_SDA'},(91,58),'ui',
    mpn='1x4 2.54mm OLED socket',assembly='HAND',rotation=90)
r('R40','4.7k','+3V3','I2C_SCL',(104,58),'ui')
r('R41','4.7k','+3V3','I2C_SDA',(108,58),'ui')
c('C42','100n','+3V3','GND',(104,62),'ui')
for i,(name,x) in enumerate([('MODE',83),('DOWN',98),('UP',113),('IO',128)]):
    add('SW'+str(i+3),name,'Switch:SW_Push','Button_Switch_SMD:SW_SPST_TL3342',
        {1:'KEY_'+name,2:'GND'},(x,139),'ui',mpn='TL3342F160QG')
    r('R'+str(i+42),'10k','+3V3','KEY_'+name,(x,133),'ui')
    c('C'+str(i+43),'100n','KEY_'+name,'GND',(x,130),'ui')
add('D1','GREEN','Device:LED','LED_SMD:LED_0603_1608Metric',{1:'GND',2:'LED_A'},(119,70),'ui',mpn='LTST-C190KGKT')
r('R46','1k','STATUS_LED','LED_A',(119,74),'ui')
for i,xy in enumerate([(54,54),(144,54),(54,144),(144,144)],1):
    add('H'+str(i),'M3 NPTH','Mechanical:MountingHole','MountingHole:MountingHole_3.2mm_M3',{},xy,'mechanical',assembly='MECHANICAL')

# Placement refinements after courtyard review.
MOVES={'C6':(79,78),'C5':(85,73),'FB1':(91,78),'C21':(88,104),'R5':(120,100.8),'R6':(120,98.5),'C10':(118,94),
       'U5':(73,89),'C23':(79,89),
       'R20':(64,62),'R21':(69,62),'C24':(64,66),'C25':(71,67),'R22':(77,62),
       'R25':(64,72),'R26':(69,72),'C29':(64,76),'C30':(72,77),'R27':(77,72),
       'R30':(71,112),'C35':(71,115),'R35':(83,112),'C40':(83,115),'R13':(88,112)}
for p in PARTS:
    if p['ref'] in MOVES:p['x'],p['y']=MOVES[p['ref']]
    if p['ref'] in ['J2','J3']:p['rotation']=270
    if p['ref'] in ['R5','R6']:p['rotation']=0

# Explicit orderable MPNs. JLC inventory/classification is checked separately;
# a blank LCSC field is deliberate and must be matched before ordering.
RESISTORS={'5.1k':'RC0603FR-075K1L','1k':'RC0603FR-071KL','22':'RC0603FR-0722RL',
 '100k':'RC0603FR-07100KL','33':'RC0603FR-0733RL','10k':'RC0603FR-0710KL',
 '220k':'RC0603FR-07220KL','100':'RC0603FR-07100RL','3.3k':'RC0603FR-073K3L','4.7k':'RC0603FR-074K7L'}
CAPACITORS={'100n':'GRM188R71C104KA01D','1u':'GRM188R71C105KA12D','2.2u':'GRM188R61C225KE15D',
 '4.7u':'GRM188R61C475KE11D','470p':'GRM1885C1H471JA01D','2.2n':'GRM1885C1H222JA01D',
 '1n':'GRM1885C1H102JA01D','10n':'GRM188R71E103KA01D'}
for p in PARTS:
    if p['symbol']=='Device:R':p['mpn']=RESISTORS[p['value']]
    if p['symbol']=='Device:C':p['mpn']=CAPACITORS[p['value']]
JLC_RESISTORS={'10k':('1002','C25804'),'1k':('1001','C21190'),'100k':('1003','C25803'),
 '4.7k':('4701','C23162'),'5.1k':('5101','C23186'),'22':('220J','C23345'),
 '100':('1000','C22775'),'3.3k':('3301','C22978'),'33':('330J','C23140'),'220k':('2203','C22961')}
for p in PARTS:
    p['sourcing_status']='UNVERIFIED'
    p['source_url']=''
    if p['symbol']=='Device:R':
        code,p['lcsc']=JLC_RESISTORS[p['value']];p['mpn']='0603WAF'+code+'T5E'
        p['sourcing_status']='BASIC' if p['value'] not in ['33','220k'] else 'JLC_LISTED'
    elif p['symbol']=='Device:C' and p['value']=='100n':
        p['mpn']='CC0603KRX7R9BB104';p['lcsc']='C14663';p['sourcing_status']='BASIC'
    elif p['ref'] in ['J1','U1','U3']:p['sourcing_status']='JLC_LISTED'
    elif p['ref']=='U2':p['sourcing_status']='LCSC_LISTED_JLC_UNCONFIRMED'
    elif p['assembly'] in ['HAND','MECHANICAL']:p['sourcing_status']=p['assembly']
    if p['lcsc']:p['source_url']='https://jlcpcb.com/partdetail/'+p['lcsc']
    if p['ref']=='U2':p['source_url']='https://www.lcsc.com/product-detail/C2651841.html'

PAGES=['mcu','power','usb','codec','analog','ui']
