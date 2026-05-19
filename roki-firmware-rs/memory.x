MEMORY
{
    /* SoftDevice s140 v7.3.x uses ~0x26000 bytes (152 KB) from flash start */
    /* Adjust if using a different SoftDevice version */
    RAM (rwx) : ORIGIN = 0x20000000 + 0x26000, LENGTH = 0x40000 - 0x26000
    FLASH (rx) : ORIGIN = 0x26000, LENGTH = 0x100000 - 0x26000
}
