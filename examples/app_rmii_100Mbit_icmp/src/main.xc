// Copyright 2014-2021 XMOS LIMITED.
// This Software is subject to the terms of the XMOS Public Licence: Version 1.
#include <xs1.h>
#include <platform.h>
#include "otp_board_info.h"
#include "ethernet.h"
#include "icmp.h"
#include "smi.h"
#include "xk_eth_xu316_dual_100m/board.h"
#include "debug_print.h"

//#include "ports_rmii.h"

rmii_data_port_t p_eth_rxd = {{PHY_0_RXD_4B, USE_LOWER_2B}};
rmii_data_port_t p_eth_txd = {{PHY_0_TXD_4B, USE_LOWER_2B}};

port p_eth_clk = CLK_50M;
port p_eth_rxdv = PHY_0_RXDV;
port p_eth_txen = PHY_0_TX_EN;

clock eth_rxclk = on tile[0]: XS1_CLKBLK_1;
clock eth_txclk = on tile[0]: XS1_CLKBLK_2;

port p_smi_mdio   = MDIO;
port p_smi_mdc    = MDC;


// These ports are for accessing the OTP memory
otp_ports_t otp_ports = on tile[0]: OTP_PORTS_INITIALIZER;

static unsigned char ip_address[4] = {192, 168, 1, 178};

// An enum to manage the array of connections from the ethernet component
// to its clients.
enum eth_clients {
  ETH_TO_ICMP,
  NUM_ETH_CLIENTS
};

enum cfg_clients {
  CFG_TO_ICMP,
  CFG_TO_PHY_DRIVER,
  NUM_CFG_CLIENTS
};

[[combinable]]
void lan8710a_phy_driver(client interface smi_if smi,
                         client interface ethernet_cfg_if eth) {
  ethernet_link_state_t link_state = ETHERNET_LINK_DOWN;
  ethernet_speed_t link_speed = LINK_100_MBPS_FULL_DUPLEX;
  const int link_poll_period_ms = 1000;
  const int phy_address = 0x0;
  timer tmr;
  int t;
  tmr :> t;

  while (smi_phy_is_powered_down(smi, phy_address));
  smi_configure(smi, phy_address, LINK_100_MBPS_FULL_DUPLEX, SMI_ENABLE_AUTONEG);

  while (1) {
    select {
    case tmr when timerafter(t) :> t:
      ethernet_link_state_t new_state = smi_get_link_state(smi, phy_address);
      // Read LAN8710A status register bit 2 to get the current link speed
      if ((new_state == ETHERNET_LINK_UP) &&
         ((smi.read_reg(phy_address, 0x1F) >> 2) & 1)) {
        link_speed = LINK_10_MBPS_FULL_DUPLEX;
      }
      else {
        link_speed = LINK_100_MBPS_FULL_DUPLEX;
      }
      if (new_state != link_state) {
        link_state = new_state;
        eth.set_link_state(0, new_state, link_speed);
      }
      t += link_poll_period_ms * XS1_TIMER_KHZ;
      break;
    }
  }
}

#define ETH_RX_BUFFER_SIZE_WORDS 1600
const int phy_address = 0x0;
int main()
{
  ethernet_cfg_if i_cfg[NUM_CFG_CLIENTS];
  ethernet_rx_if i_rx[NUM_ETH_CLIENTS];
  ethernet_tx_if i_tx[NUM_ETH_CLIENTS];
  smi_if i_smi;

  par {
    on tile[0]: unsafe{rmii_ethernet_rt_mac(i_cfg, NUM_CFG_CLIENTS,
                                          i_rx, NUM_ETH_CLIENTS,
                                          i_tx, NUM_ETH_CLIENTS,
                                          null, null,
                                          p_eth_clk,
                                          &p_eth_rxd, p_eth_rxdv,
                                          p_eth_txen, &p_eth_txd,
                                          eth_rxclk, eth_txclk,
                                          4000, 4000, ETHERNET_DISABLE_SHAPER);}

    on tile[1]: dp83826e_phy_driver(i_smi, i_cfg[CFG_TO_PHY_DRIVER], phy_address);
    on tile[1]: smi(i_smi, p_smi_mdio, p_smi_mdc);

    on tile[0]: icmp_server(i_cfg[CFG_TO_ICMP],
                            i_rx[ETH_TO_ICMP], i_tx[ETH_TO_ICMP],
                            ip_address, otp_ports);
  }
  return 0;
}
