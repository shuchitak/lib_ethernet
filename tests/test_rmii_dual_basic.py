# Copyright 2014-2024 XMOS LIMITED.
# This Software is subject to the terms of the XMOS Public Licence: Version 1.

import random
import Pyxsim as px
from pathlib import Path
import pytest
import sys, os

from mii_packet import MiiPacket
from mii_clock import Clock
from helpers import packet_processing_time, get_dut_mac_address
from helpers import choose_small_frame_size, run_parametrised_test_rx #check_received_packet 
from helpers import generate_tests, create_if_needed, create_expect, get_sim_args
from helpers import get_rmii_clk, get_rmii_tx_phy, get_rmii_rx_phy
from rmii_phy import RMiiTransmitter, RMiiReceiver



def do_rx_test_dual(capfd, mac, arch, rx_clk, rx_phy, tx_clk, tx_phy, packets, test_file, seed,
               extra_tasks=[], override_dut_dir=False, rx_width=None, tx_width=None):

    """ Shared test code for all RX tests using the test_rx application.
    """
    testname,extension = os.path.splitext(os.path.basename(test_file))

    with capfd.disabled():
        print(f"Running {testname}: {mac} {[phy.get_name() for phy in tx_phy]} phy, {arch}, rx_width {rx_width} arch at {tx_clk.get_name()} (seed = {seed})")
    capfd.readouterr() # clear capfd buffer

    profile = f'{mac}_{tx_phy[0].get_name()}'
    if rx_width:
        profile = profile + f"_rx{rx_width}"
    if tx_width:
        profile = profile + f"_tx{tx_width}"
    profile = profile + f"_{arch}"

    dut_dir = override_dut_dir if override_dut_dir else testname
    binary = f'{dut_dir}/bin/{profile}/{dut_dir}_{profile}.xe'
    assert os.path.isfile(binary), f"Missing .xe {binary}"

    tx_phy[0].set_packets(packets)
    for phy in rx_phy:
        phy.set_expected_packets(packets)

    expect_folder = create_if_needed("expect_temp")
    if rx_width:
        expect_filename = f'{expect_folder}/{testname}_{mac}_{tx_phy[0].get_name()}_{rx_width}_{tx_width}_{tx_clk.get_name()}_{arch}.expect'
    else:
        expect_filename = f'{expect_folder}/{testname}_{mac}_{tx_phy[0].get_name()}_{tx_clk.get_name()}_{arch}.expect'

    create_expect(packets, expect_filename)

    tester = px.testers.ComparisonTester(open(expect_filename))
    tester = None

    simargs = get_sim_args(testname, mac, tx_clk, tx_phy[0], arch)
    print(simargs)
 
    st = [tx_clk, rx_phy[0], rx_phy[1], tx_phy[0], tx_phy[1]]


    result = px.run_on_simulator_(  binary,
                                    simthreads=st + extra_tasks,
                                    tester=tester,
                                    simargs=simargs,
                                    do_xe_prebuild=False,
                                    capfd=capfd
                                    )

    assert result is True, f"{result}"


def move_to_next_valid_packet(phy):
    while (phy.expect_packet_index < phy.num_expected_packets and
           phy.expected_packets[phy.expect_packet_index].dropped):
        phy.expect_packet_index += 1


def check_received_packet(packet, phy):
    if phy.expected_packets is None:
        return

    move_to_next_valid_packet(phy)

    print(packet, packet.num_data_bytes, packet.ether_len_type)
    print(packet.data_bytes)


    
def rmii_dual_test(capfd, params, seed):
    verbose = False
    with capfd.disabled():
        clk = get_rmii_clk(Clock.CLK_50MHz)
        tx_rmii_phy = get_rmii_tx_phy(params['rx_width'],
                                      clk,
                                      verbose=verbose
                                      )

        tx_rmii_phy_2 = get_rmii_tx_phy(params['rx_width'],
                                      clk,
                                      verbose=verbose,
                                      second_phy=True
                                      )

        rx_rmii_phy = get_rmii_rx_phy(params['tx_width'],
                                      clk,
                                      packet_fn=check_received_packet,
                                      verbose=verbose
                                      )

        rx_rmii_phy_2 = get_rmii_rx_phy(params['tx_width'],
                                      clk,
                                      packet_fn=check_received_packet,
                                      verbose=verbose,
                                      second_phy=True
                                      )

        mac, arch, rx_clk, rx_phy, tx_clk, tx_phy, rx_width, tx_width = params["mac"], params["arch"], None, [rx_rmii_phy, rx_rmii_phy_2], clk, [tx_rmii_phy, tx_rmii_phy_2], params['rx_width'],params['tx_width']

        rand = random.Random()
        rand.seed(seed)

        dut_mac_address = get_dut_mac_address()
        broadcast_mac_address = [0xff, 0xff, 0xff, 0xff, 0xff, 0xff]

        packets = []

        # Send frames which excercise all of the tail length vals (0, 1, 2, 3 bytes)
        packet_start_len = 100
        for i in range(5): 
            packets.append(MiiPacket(rand,
                dst_mac_addr=dut_mac_address,
                create_data_args=['step', (i, packet_start_len + i)],
                inter_frame_gap=packet_processing_time(tx_phy[0], packet_start_len, mac),
            ))

        do_rx_test_dual(capfd, mac, arch, rx_clk, rx_phy, tx_clk, tx_phy, packets, __file__, seed, rx_width=rx_width, tx_width=tx_width)



test_params_file = Path(__file__).parent / "test_rmii_dual_basic/test_params.json"
@pytest.mark.parametrize("params", generate_tests(test_params_file)[0], ids=generate_tests(test_params_file)[1])
def test_rx(capfd, seed, params):
    with capfd.disabled():
        print(params)

    if seed == None:
        seed = random.randint(0, sys.maxsize)

    rmii_dual_test(capfd, params, seed)

