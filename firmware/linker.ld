ENTRY(Reset_Handler)
MEMORY {
  FLASH (rx) : ORIGIN = 0x08000000, LENGTH = 2048K
  RAM (rwx) : ORIGIN = 0x24000000, LENGTH = 512K
  DTCM (rwx) : ORIGIN = 0x20000000, LENGTH = 128K
  DMA_RAM (rw) : ORIGIN = 0x30000000, LENGTH = 32K
}
_estack = ORIGIN(DTCM) + LENGTH(DTCM);
SECTIONS {
  .isr_vector : { KEEP(*(.isr_vector)) } > FLASH
  .text : { *(.text*) *(.rodata*) KEEP(*(.init)) KEEP(*(.fini)) . = ALIGN(4); } > FLASH
  .ARM.extab : { *(.ARM.extab*) } > FLASH
  .ARM.exidx : { __exidx_start = .; *(.ARM.exidx*) __exidx_end = .; } > FLASH
  .preinit_array : { PROVIDE_HIDDEN(__preinit_array_start = .); KEEP(*(.preinit_array*)) PROVIDE_HIDDEN(__preinit_array_end = .); } > FLASH
  .init_array : { PROVIDE_HIDDEN(__init_array_start = .); KEEP(*(SORT(.init_array.*))) KEEP(*(.init_array*)) PROVIDE_HIDDEN(__init_array_end = .); } > FLASH
  .fini_array : { PROVIDE_HIDDEN(__fini_array_start = .); KEEP(*(.fini_array*)) PROVIDE_HIDDEN(__fini_array_end = .); } > FLASH
  _sidata = LOADADDR(.data);
  .data : { . = ALIGN(4); _sdata = .; *(.data*) . = ALIGN(4); _edata = .; } > RAM AT > FLASH
  .bss (NOLOAD) : { . = ALIGN(8); _sbss = .; *(.bss*) *(COMMON) . = ALIGN(8); _ebss = .; end = .; _end = .; } > RAM
  .dma (NOLOAD) : { . = ALIGN(32); *(.dma*) . = ALIGN(32); } > DMA_RAM
  /DISCARD/ : { *(.note.GNU-stack) }
}
ASSERT(SIZEOF(.dma) <= LENGTH(DMA_RAM), "DMA RAM overflow")
