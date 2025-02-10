from scapy.all import *
import threading
from pathlib import Path
import random
import copy
from mii_packet import MiiPacket
from hardware_test_tools.XcoreApp import XcoreApp
from hw_helpers import mii2scapy, scapy2mii, get_mac_address
import pytest
from contextlib import nullcontext
import time
from xcore_app_control import XcoreAppControl, SocketHost
from xcore_app_control import scapy_send_l2_pkts_loop, scapy_send_l2_pkt_sequence
import re
import subprocess
import platform


pkg_dir = Path(__file__).parent


@pytest.mark.parametrize('send_method', ['socket'])
def test_hw_mii_rx_only(request, send_method):
    adapter_id = request.config.getoption("--adapter-id")
    assert adapter_id != None, "Error: Specify a valid adapter-id"

    eth_intf = request.config.getoption("--eth-intf")
    assert eth_intf != None, "Error: Specify a valid ethernet interface name on which to send traffic"

    test_duration_s = request.config.getoption("--test-duration")
    if not test_duration_s:
        test_duration_s = 0.4
    test_duration_s = float(test_duration_s)

    verbose = False
    seed = 0
    rand = random.Random()
    rand.seed(seed)

    payload_len = 'max'

    host_mac_address_str = get_mac_address(eth_intf)
    assert host_mac_address_str, f"get_mac_address() couldn't find mac address for interface {eth_intf}"
    print(f"host_mac_address = {host_mac_address_str}")

    dut_mac_address_str = "10:11:12:13:14:15 12:34:56:78:9a:bc 11:33:55:77:88:00"
    print(f"dut_mac_address = {dut_mac_address_str}")

    dut_mac_addresses = []
    for m in dut_mac_address_str.split():
        dut_mac_address = [int(i, 16) for i in m.split(":")]
        dut_mac_addresses.append(dut_mac_address)

    print(f"dut_mac_addresses = {dut_mac_addresses}")

    host_mac_address = [int(i, 16) for i in host_mac_address_str.split(":")]


    ethertype = [0x22, 0x22]
    num_packets = 0
    packets = []


    # Create packets
    print(f"Generating {test_duration_s} seconds of packet sequence")

    if payload_len == 'max':
        num_data_bytes = 1500
    elif payload_len == 'random':
        num_data_bytes = random.randint(46, 1500)
    else:
        assert False


    packet_duration_bits = (14 + num_data_bytes + 4)*8 + 64 + 96 # Assume Min IFG

    test_duration_bits = test_duration_s * 100e6
    num_packets = int(float(test_duration_bits)/packet_duration_bits)
    print(f"Going to test {num_packets} packets")

    if send_method == "socket":
        assert platform.system() in ["Linux"], f"Sending using sockets only supported on Linux"
        socket_host = SocketHost(eth_intf, host_mac_address_str, dut_mac_address_str)
    else:
        assert False, f"Invalid send_method {send_method}"


    xe_name = pkg_dir / "hw_test_mii" / "bin" / "rx_multiple_queues" / "hw_test_mii_rx_multiple_queues.xe"
    xcoreapp = XcoreAppControl(adapter_id, xe_name, attach="xscope_app")
    xcoreapp.__enter__()

    print("Wait for DUT to be ready")
    stdout, stderr = xcoreapp.xscope_controller_cmd_connect()
    if verbose:
        print(stderr)

    print("Set DUT Mac address for each RX client")
    for i,m in enumerate(dut_mac_address_str.split()):
        stdout, stderr = xcoreapp.xscope_controller_cmd_set_dut_macaddr(i, m)
        if verbose:
            print(f"stdout = {stdout}")
            print(f"stderr = {stderr}")

    print(f"Send {num_packets} packets now")
    send_time = []

    if send_method == "socket":
        socket_host.send(num_packets)

    print("Retrive status and shutdown DUT")
    stdout, stderr = xcoreapp.xscope_controller_cmd_shutdown()

    if verbose:
        print(stderr)

    print("Terminating!!!")
    xcoreapp.terminate()

    errors = []

    # Check for any seq id mismatch errors reported by the DUT
    matches = re.findall(r"^DUT ERROR:.*", stderr, re.MULTILINE)
    if matches:
        errors.append(f"ERROR: DUT logs report errors.")
        for m in matches:
            errors.append(m)

    client_index = 0
    m = re.search(fr"DUT client index {client_index}: Received (\d+) bytes, (\d+) packets", stderr)

    if not m or len(m.groups()) < 2:
        errors.append(f"ERROR: DUT does not report received bytes and packets")
    else:
        bytes_received, packets_received = map(int, m.groups())
        if int(packets_received) != num_packets:
            errors.append(f"ERROR: Packets dropped. Sent {num_packets}, DUT Received {packets_received}")

    if len(errors):
        error_msg = "\n".join(errors)
        assert False, f"Various errors reported!!\n{error_msg}\n\nDUT stdout = {stderr}"





