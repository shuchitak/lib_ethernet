#ifndef __mii_buffering_defines_h__
#define __mii_buffering_defines_h__

// The number of bytes in the mii_packet_t before the data
#define MII_PACKET_HEADER_BYTES 36
#define MII_PACKET_HEADER_WORDS (MII_PACKET_HEADER_BYTES / 4)

// The amount of space required for the common interrupt handler
#define MII_COMMON_HANDLER_STACK_WORDS 4

#endif //__mii_buffering_defines_h__
