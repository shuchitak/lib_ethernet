// Copyright 2024 XMOS LIMITED.
// This Software is subject to the terms of the XMOS Public Licence: Version 1.
#include <xs1.h>
#include <platform.h>
#include <stdio.h>
#include <stdlib.h>
#include <assert.h>
#include <print.h>
#include "ethernet.h"

port p_eth_clk = XS1_PORT_1O;

#ifndef USE_LOWER
#define USE_LOWER 1
#endif

#if TX_WIDTH == 4
#if USE_LOWER
rmii_data_port_t p_eth_txd_0 = {{XS1_PORT_4B, USE_LOWER_2B}};
rmii_data_port_t p_eth_txd_1 = {{XS1_PORT_4D, USE_LOWER_2B}};
#else
rmii_data_port_t p_eth_txd_0 = {{XS1_PORT_4B, USE_UPPER_2B}};
rmii_data_port_t p_eth_txd_1 = {{XS1_PORT_4D, USE_UPPER_2B}};
#endif
#elif TX_WIDTH == 1
rmii_data_port_t p_eth_txd_0 = {{XS1_PORT_1C, XS1_PORT_1D}};
rmii_data_port_t p_eth_txd_1 = {{XS1_PORT_1E, XS1_PORT_1F}};
#else
#error invalid TX_WIDTH
#endif

#if RX_WIDTH == 4
#if USE_LOWER
rmii_data_port_t p_eth_rxd_0 = {{XS1_PORT_4A, USE_LOWER_2B}};
rmii_data_port_t p_eth_rxd_1 = {{XS1_PORT_4C, USE_LOWER_2B}};
#else
rmii_data_port_t p_eth_rxd_0 = {{XS1_PORT_4A, USE_UPPER_2B}};
rmii_data_port_t p_eth_rxd_1 = {{XS1_PORT_4C, USE_UPPER_2B}};
#endif
#elif RX_WIDTH == 1
rmii_data_port_t p_eth_rxd_0 = {{XS1_PORT_1A, XS1_PORT_1B}};
rmii_data_port_t p_eth_rxd_1 = {{XS1_PORT_1H, XS1_PORT_1I}};
#else
#error invalid RX_WIDTH
#endif

port p_eth_rxdv_0 = XS1_PORT_1K;
port p_eth_rxdv_1 = XS1_PORT_1J;
port p_eth_txen_0 = XS1_PORT_1L;
port p_eth_txen_1 = XS1_PORT_1M;
clock eth_rxclk_0 = XS1_CLKBLK_1;
clock eth_txclk_0 = XS1_CLKBLK_2;
clock eth_rxclk_1 = XS1_CLKBLK_3;
clock eth_txclk_1 = XS1_CLKBLK_4;


// Test harness
clock eth_clk_harness = XS1_CLKBLK_5;
port p_eth_clk_harness = XS1_PORT_1N;

#define MAX_PACKET_WORDS ((ETHERNET_MAX_PACKET_SIZE + 3) / 4)

#define VLAN_TAGGED 1

#define MII_CREDIT_FRACTIONAL_BITS 16

static int calc_idle_slope(int bps)
{
  long long slope = ((long long) bps) << (MII_CREDIT_FRACTIONAL_BITS);
  slope = slope / 100000000; // bits that should be sent per ref timer tick

  return (int) slope;
}

static void printbytes(char *b, int n){
    for(int i=0; i<n;i++){
        printstr(", 0x"); printhex(b[i]);
    }
    printstr("\n");
}

static void printwords_1b(unsigned *b, int n){
    for(int i=0; i<n;i++){
        // printstr(", 0x"); printhex(b[i]);
        uint64_t combined = (uint64_t)b[i];
        uint32_t p0_val, p1_val;
        {p1_val, p0_val} = unzip(combined, 0);
        printhex(b[i]); printstr(", 0x");printhex(p0_val); printstr(", 0x");printhexln(p1_val);
    }
    printstr("\n");
}


static void printwords_4b(unsigned *b, int n){
    for(int i=0; i<n;i++){
        uint64_t zipped = zip(0, b[i], 1); // lower
        uint32_t p0_val = zipped & 0xffffffff;
        uint32_t p1_val = zipped >> 32;
        printhex(b[i]); printstr(", 0x");printhex(p0_val); printstr(", 0x");printhexln(p1_val);
    }
    printstr("\n");
}



void test_app(client ethernet_cfg_if i_cfg,
                client ethernet_rx_if i_rx,
                streaming chanend c_rx_hp,
                client ethernet_tx_if tx_lp,
                streaming chanend c_tx_hp)
{
    // Request 5Mbits/sec
    i_cfg.set_egress_qav_idle_slope(0, calc_idle_slope(5 * 1024 * 1024));

    unsigned tx_data[MAX_PACKET_WORDS];
    for (size_t i = 0; i < MAX_PACKET_WORDS; i++) {
      tx_data[i] = i;
    }

    // src/dst MAC addresses
    size_t j = 0;
    for (; j < 12; j++)
      ((char*)tx_data)[j] = j;

    if (VLAN_TAGGED) {
      ((char*)tx_data)[j++] = 0x81;
      ((char*)tx_data)[j++] = 0x00;
      ((char*)tx_data)[j++] = 0x00;
      ((char*)tx_data)[j++] = 0x00;
    }

    const int length = 61;
    const int header_bytes = VLAN_TAGGED ? 18 : 14;
    ((char*)tx_data)[j++] = (length - header_bytes) >> 8;
    ((char*)tx_data)[j++] = (length - header_bytes) & 0xff;

    timer tmr_tx;
    int time_tx_trig;
    tmr_tx :> time_tx_trig;

    int start_length = 80;


    ethernet_macaddr_filter_t macaddr_filter;
    size_t index = i_rx.get_index();
    for (int i = 0; i < MACADDR_NUM_BYTES; i++) {
        macaddr_filter.addr[i] = i;
    }
    i_cfg.add_macaddr_filter(index, 1, macaddr_filter);

    while (1) {
        uint8_t rxbuf[ETHERNET_MAX_PACKET_SIZE];
        ethernet_packet_info_t packet_info;
        printstr("select\n");

        select {
            case ethernet_receive_hp_packet(c_rx_hp, rxbuf, packet_info):
                printf("HP packet received: %d bytes\n", packet_info.len);
                // printbytes(rxbuf, packet_info.len);
                break;

            case i_rx.packet_ready():
                unsigned n;
                i_rx.get_packet(packet_info, rxbuf, n);
                printf("LP packet received: %d bytes\n", n);
                // printbytes(rxbuf, packet_info.len);
                break;

            case tmr_tx when timerafter(time_tx_trig) :> time_tx_trig:
                printf("TX sending: %d\n", start_length);
                // printbytes((char*)data, length);
                // printwords_4b(data, (length + 3)/4);
                tx_lp.send_packet((char *)tx_data, start_length, ETHERNET_ALL_INTERFACES);
                start_length++;
                time_tx_trig += 6000;
                break;
        }
    }
}


int main()
{
    ethernet_cfg_if i_cfg[1];
    ethernet_rx_if i_rx_lp[1];
    ethernet_tx_if i_tx_lp[1];
    streaming chan c_rx_hp;
    streaming chan c_tx_hp;


    // Setup 50M clock
    unsigned divider = 2; // 100 / 2 = 50;
    configure_clock_ref(eth_clk_harness, divider / 2);
    set_port_clock(p_eth_clk_harness, eth_clk_harness);
    set_port_mode_clock(p_eth_clk_harness);
    start_clock(eth_clk_harness);

    par {
        unsafe{rmii_ethernet_rt_mac_dual(i_cfg, 1,
                                        i_rx_lp, 1,
                                        i_tx_lp, 1,
                                        c_rx_hp, c_tx_hp,
                                        p_eth_clk,
                                        &p_eth_rxd_0, p_eth_rxdv_0,
                                        p_eth_txen_0, &p_eth_txd_0,
                                        eth_rxclk_0, eth_txclk_0,
                                        &p_eth_rxd_1, p_eth_rxdv_1,
                                        p_eth_txen_1, &p_eth_txd_1,
                                        eth_rxclk_1, eth_txclk_1,
                                        4000, 4000, ETHERNET_ENABLE_SHAPER);}

        test_app(i_cfg[0], i_rx_lp[0], c_rx_hp, i_tx_lp[0], c_tx_hp);
    }

    return 0;
}
