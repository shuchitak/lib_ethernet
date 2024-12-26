#include <xs1.h>

    .section .cp.rodata,     "ac", @progbits
    .align 4
.cc_top rmiiconsts.data
initial_crc:
    .word 0x9226F562
expected_preamble:
    .word 0xD5555555
inverted_crc:
    .word 0x6DD90A9D
.cc_bottom rmiiconsts.data

.cc_top receive_full_preamble_1b_with_select_asm.func, receive_full_preamble_1b_with_select_asm

#define STACK_WORDS                 4
#define RXD0        r0  // Port resource ID
#define RXD1        r1  // Port resource ID

//Call: unsigned crc = receive_full_preamble_1b_with_select_asm(p_mii_rxd_0, p_mii_rxd_1, p_mii_rxdv);
// r0: p_mii_rxd_0
// r1: p_mii_rxd_1
// r2: p_mii_rxdv

.globl receive_full_preamble_1b_with_select_asm.nstackwords
.globl receive_full_preamble_1b_with_select_asm.maxthreads
.globl receive_full_preamble_1b_with_select_asm.maxtimers
.globl receive_full_preamble_1b_with_select_asm.maxchanends
.globl receive_full_preamble_1b_with_select_asm.maxsync
.type  receive_full_preamble_1b_with_select_asm, @function
.linkset receive_full_preamble_1b_with_select_asm.locnoside, 0
.linkset receive_full_preamble_1b_with_select_asm.nstackwords, STACK_WORDS
.linkset receive_full_preamble_1b_with_select_asm.maxchanends, 0
.linkset receive_full_preamble_1b_with_select_asm.maxtimers, 0
.linkset receive_full_preamble_1b_with_select_asm.maxthreads, 0
.linkset receive_full_preamble_1b_with_select_asm.maxsync, 0

.globl receive_full_preamble_1b_with_select_asm
    .align 8
    .issue_mode dual
receive_full_preamble_1b_with_select_asm:
    dualentsp 0x0
    extsp 0x2
    std r5, r4, sp[0x0]
    ldc r5, 0x10


    setpsc res[r0], r5
    setpsc res[r1], r5
    mkmsk r3, 1

    clre
    eeu res[r0]
    ldap r11, rx_data_received
    setv res[r0], r11

    setd res[r2], r3
    setc res[r2], 0x11
    in r3, res[r2]

    eeu res[r2]
    ldc r3, 0
    setd res[r2], r3
    ldap r11, data_valid_deasserted
    setv res[r2], r11
    ldc r11, 0x2

    waiteu

rx_data_received:
    in r3, res[r0]
    in r4, res[r1]
    sub r11, r11, 0x1
    bf r11, preamble_done
    setpsc res[r0], r5
    setpsc res[r1], r5
    waiteu

data_valid_deasserted:
    in r0, res[r2]
    bu done

preamble_done:
    zip r4, r3, 0x0
    ldw r0, cp[expected_preamble]
    eq r0, r4, r0
    bt r0, preamble_match
    ldw r0, cp[inverted_crc]
    bu done
preamble_match:
    ldw r0, cp[initial_crc]
done:
    ldd r5, r4, sp[0x0]
    ldaw sp, sp[0x2]
    retsp 0x0




.cc_bottom receive_full_preamble_1b_with_select_asm.func
