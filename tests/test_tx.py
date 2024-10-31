# Copyright 2014-2024 XMOS LIMITED.
# This Software is subject to the terms of the XMOS Public Licence: Version 1.
import Pyxsim as px
import os
import sys
from mii_clock import Clock
from mii_phy import MiiReceiver
from rgmii_phy import RgmiiTransmitter
from mii_packet import MiiPacket
from helpers import get_sim_args, run_on
from helpers import get_mii_rx_clk_phy, get_rgmii_rx_clk_phy
from helpers import get_mii_tx_clk_phy, get_rgmii_tx_clk_phy

def packet_checker(packet, phy):
    print("Packet received:")
    sys.stdout.write(packet.dump(show_ifg=False))

    # Ignore the CRC bytes (-4)
    data = packet.data_bytes[:-4]

    if len(data) < 2:
        print(f"ERROR: packet doesn't contain enough data ({len(data)} bytes)")
        return

    step = data[1] - data[0]
    print(f"Step = {step}.")

    for i in range(len(data)-1):
        x = data[i+1] - data[i]
        x = x & 0xff;
        if x != step:
            print(f"ERROR: byte {i+1} is {x} more than byte %d (expected {step}).")
            # Only print one error per packet
            break

def do_test(mac, arch, rx_clk, rx_phy, tx_clk, tx_phy):
    testname = 'test_tx'

    binary = f'{testname}/bin/{testname}.xe'
    # binary = f'{testname}/bin/{mac}_{rx_phy.get_name()}_{arch}/{testname}_{mac}_{rx_phy.get_name()}_{arch}.xe'

    print(f"Running {testname}: {mac} {rx_phy.get_name()} phy, {arch} arch at {rx_clk.get_name()}")

    # tester = px.testers.ComparisonTester(open('{test}.expect'.format(test=testname)),
    #                                  'lib_ethernet', 'basic_tests', testname,
    #                                  {'mac':mac, 'phy':rx_phy.get_name(), 'clk':rx_clk.get_name(), 'arch':arch})

    tester = px.testers.ComparisonTester(open(f'{testname}.expect'))

    simargs = get_sim_args(testname, mac, rx_clk, rx_phy)
    print(testname, mac, rx_clk, rx_phy)
    print(simargs)
    px.run_on_simulator_(   binary,
                            simthreads=[rx_clk, rx_phy, tx_clk, tx_phy],
                            tester=tester,
                            simargs=simargs,
                            do_xe_prebuild=False)

def runtest():
    # Even though this is a TX-only test, both PHYs are needed in order to drive the mode pins for RGMII

    # Test 100 MBit - MII XS1
    # (rx_clk_25, rx_mii) = get_mii_rx_clk_phy(packet_fn=packet_checker, test_ctrl='tile[0]:XS1_PORT_1C')
    # (tx_clk_25, tx_mii) = get_mii_tx_clk_phy(do_timeout=False)
    # if run_on(phy='mii', clk='25Mhz', mac='standard', arch='xs1'):
    #     do_test('standard', 'xs1', rx_clk_25, rx_mii, tx_clk_25, tx_mii)
    # if run_on(phy='mii', clk='25Mhz', mac='rt', arch='xs1'):
    #     do_test('rt',  'xs1', rx_clk_25, rx_mii, tx_clk_25, tx_mii)
    # if run_on(phy='mii', clk='25Mhz', mac='rt_hp', arch='xs1'):
    #     do_test('rt_hp', 'xs1', rx_clk_25, rx_mii, tx_clk_25, tx_mii)

    # Test 100 MBit - MII XS2
    (rx_clk_25, rx_mii) = get_mii_rx_clk_phy(packet_fn=packet_checker, test_ctrl='tile[0]:XS1_PORT_1C')
    (tx_clk_25, tx_mii) = get_mii_tx_clk_phy(do_timeout=False)
    if run_on(phy='mii', clk='25Mhz', mac='standard', arch='xs2'):
        do_test('standard', 'xs2', rx_clk_25, rx_mii, tx_clk_25, tx_mii)
    if run_on(phy='mii', clk='25Mhz', mac='rt', arch='xs2'):
        do_test('rt', 'xs2', rx_clk_25, rx_mii, tx_clk_25, tx_mii)
    if run_on(phy='mii', clk='25Mhz', mac='rt_hp', arch='xs2'):
        do_test('rt_hp', 'xs2', rx_clk_25, rx_mii, tx_clk_25, tx_mii)

    # Test 100 MBit - RGMII
    # (rx_clk_25, rx_rgmii) = get_rgmii_rx_clk_phy(Clock.CLK_25MHz, packet_fn=packet_checker,
    #                                             test_ctrl='tile[0]:XS1_PORT_1C')
    # (tx_clk_25, tx_rgmii) = get_rgmii_tx_clk_phy(Clock.CLK_25MHz, do_timeout=False)
    # if run_on(phy='rgmii', clk='25Mhz', mac='rt', arch='xs2'):
    #     do_test('rt', 'xs2', rx_clk_25, rx_rgmii, tx_clk_25, tx_rgmii)
    # if run_on(phy='rgmii', clk='25Mhz', mac='rt_hp', arch='xs2'):
    #     do_test('rt_hp', 'xs2', rx_clk_25, rx_rgmii, tx_clk_25, tx_rgmii)

    # Test 1000 MBit - RGMII
    # (rx_clk_125, rx_rgmii) = get_rgmii_rx_clk_phy(Clock.CLK_125MHz, packet_fn=packet_checker,
    #                                            test_ctrl='tile[0]:XS1_PORT_1C')
    # (tx_clk_125, tx_rgmii) = get_rgmii_tx_clk_phy(Clock.CLK_125MHz, do_timeout=False)
    # if run_on(phy='rgmii', clk='125Mhz', mac='rt', arch='xs2'):
    #     do_test('rt', 'xs2', rx_clk_125, rx_rgmii, tx_clk_125, tx_rgmii)
    # if run_on(phy='rgmii', clk='125Mhz', mac='rt_hp', arch='xs2'):
    #     do_test('rt_hp', 'xs2', rx_clk_125, rx_rgmii, tx_clk_125, tx_rgmii)


def test_tx():
    runtest()