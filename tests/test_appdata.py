# Copyright 2014-2024 XMOS LIMITED.
# This Software is subject to the terms of the XMOS Public Licence: Version 1.

import os
import sys
import json
from pathlib import Path
import pytest
import random
import Pyxsim as px

from mii_clock import Clock
from mii_phy import MiiTransmitter, MiiReceiver
from rgmii_phy import RgmiiTransmitter, RgmiiReceiver
from mii_packet import MiiPacket
from helpers import do_rx_test, get_dut_mac_address, check_received_packet, packet_processing_time
from helpers import get_sim_args, get_mii_tx_clk_phy, get_rgmii_tx_clk_phy

with open(Path(__file__).parent / "test_appdata/test_params.json") as f:
    params = json.load(f)

def do_test(capfd, mac, arch, tx_clk, tx_phy):
    testname = 'test_appdata'

    profile = f'{mac}_{tx_phy.get_name()}'
    binary = f'{testname}/bin/{profile}/{testname}_{profile}.xe'
    assert os.path.isfile(binary)

    with capfd.disabled():
        print(f"Running {testname}: {tx_phy.get_name()} phy at {tx_clk.get_name()}")

    rand = random.Random()

    dut_mac_address = get_dut_mac_address()
    packets = [
        MiiPacket(rand, dst_mac_addr=[0, 1, 2, 3, 4, 7], src_mac_addr=[0 for x in range(6)],
                  ether_len_type=[0x33, 0x33], inter_frame_gap=packet_processing_time(tx_phy, 64, mac)*4,
                  data_bytes=[1,2,3,4] + [0 for x in range(60)]),
        MiiPacket(rand, dst_mac_addr=[0, 1, 2, 3, 4, 0], src_mac_addr=[0 for x in range(6)],
                  ether_len_type=[0x11, 0x11], inter_frame_gap=packet_processing_time(tx_phy, 64, mac)*4,
                  data_bytes=[1,2,3,4] + [0 for x in range(60)]),
        MiiPacket(rand, dst_mac_addr=[0, 1, 2, 3, 4, 1], src_mac_addr=[0 for x in range(6)],
                  ether_len_type=[0x22, 0x22], inter_frame_gap=packet_processing_time(tx_phy, 64, mac)*4,
                  data_bytes=[5,6,7,8] + [0 for x in range(60)]),
        MiiPacket(rand, dst_mac_addr=[0, 1, 2, 3, 4, 2], src_mac_addr=[0 for x in range(6)],
                  ether_len_type=[0x33, 0x33],
                  inter_frame_gap=packet_processing_time(tx_phy, 64, mac)*4, data_bytes=[4,3,2,1] + [0 for x in range(60)]),
        MiiPacket(rand, dst_mac_addr=[0, 1, 2, 3, 4, 3], src_mac_addr=[0 for x in range(6)],
                  ether_len_type=[0x44, 0x44], inter_frame_gap=packet_processing_time(tx_phy, 64, mac)*4,
                  data_bytes=[8,7,6,5] + [0 for x in range(60)])
      ]

    tx_phy.set_packets(packets)

    tester = px.testers.ComparisonTester(open('test_appdata_{phy}_{mac}.expect'.format(phy=tx_phy.get_name(), mac=mac)), ordered=False)
    simargs = get_sim_args(testname, mac, tx_clk, tx_phy)

    result = px.run_on_simulator_(  binary,
                                    simthreads=[tx_clk, tx_phy],
                                    tester=tester,
                                    simargs=simargs,
                                    do_xe_prebuild=False,
                                    capfd=capfd)

    assert result is True, f"{result}"

@pytest.mark.parametrize("params", params["PROFILES"], ids=["-".join(list(profile.values())) for profile in params["PROFILES"]])
def test_appdata(capfd, params):
    random.seed(1)

    # Test 100 MBit - MII XS2
    if params["phy"] == "mii":
        (tx_clk_25, tx_mii) = get_mii_tx_clk_phy(verbose=True, test_ctrl="tile[0]:XS1_PORT_1A")
        do_test(capfd, params["mac"], params["arch"], tx_clk_25, tx_mii)

    elif params["phy"] == "rgmii":
        # Test 100 MBit - RGMII
        if params["clk"] == "25MHz":
            (tx_clk_25, tx_rgmii) = get_rgmii_tx_clk_phy(Clock.CLK_25MHz, verbose=True, test_ctrl="tile[0]:XS1_PORT_1A")
            do_test(capfd, params["mac"], params["arch"], tx_clk_25, tx_rgmii)
        # Test 1000 MBit - RGMII
        elif params["clk"] == "125MHz":
            (tx_clk_125, tx_rgmii) = get_rgmii_tx_clk_phy(Clock.CLK_125MHz, verbose=True, test_ctrl="tile[0]:XS1_PORT_1A")
            do_test(capfd, params["mac"], params["arch"], tx_clk_125, tx_rgmii)
        else:
            assert 0, f"Invalid params: {params}"

    else:
        assert 0, f"Invalid params: {params}"
