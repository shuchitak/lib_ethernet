from enum import Enum, auto
import sys
import platform
from pathlib import Path
from hardware_test_tools.XcoreApp import XcoreApp
from xscope_endpoint import Endpoint, QueueConsumer

class XscopeControl():
    class XscopeCommands(Enum):
        CMD_DEVICE_SHUTDOWN = auto()
        CMD_SET_DEVICE_MACADDR = auto()
        CMD_SET_HOST_MACADDR = auto()
        CMD_HOST_SET_DUT_TX_PACKETS = auto()
        CMD_SET_DUT_RECEIVE = auto()
        CMD_DEVICE_CONNECT = auto()
        CMD_EXIT_DEVICE_MAC = auto()

        @classmethod
        def write_to_h_file(cls, filename):
            filename = Path(filename)
            dir_path = filename.parent
            dir_path.mkdir(parents=True, exist_ok=True)

            with open(filename, "w") as fp:
                name = filename.name
                name = name.replace(".", "_")
                fp.write(f"#ifndef __{name}__\n")
                fp.write(f"#define __{name}__\n\n")
                fp.write("typedef enum {\n")
                for member in cls:
                    fp.write(f"\t{member.name} = {member.value},\n")
                fp.write("}xscope_cmds_t;\n\n")
                fp.write("#endif\n")

    def __init__(self, host, port, timeout=30, verbose=False):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.verbose = verbose

    def xscope_controller_do_command(self, cmds):
        """
        Runs the xscope host app to connect to the DUT and execute a command over xscope port

        Parameters:
        xscope_controller: xscope host application binary
        cmds (list): byte list containing the command + arguments for the command that needs to be executed
        timeout: timeout in seconds for when not able to communicate with the device

        Returns:
        stdout and stderr from running the host application
        """
        ep = Endpoint()
        probe = QueueConsumer(ep, "command_ack")

        if ep.connect(hostname=self.host, port=self.port):
            print("Xscope Host app failed to connect")
            assert False
        if self.verbose:
            print(f"Sending {cmds} bytes to the device over xscope")
        ep.publish(bytes(cmds))
        ack = probe.next()
        if self.verbose:
            print(f"Received ack {ack}")

        device_stdout = ep._captured_output.getvalue() # stdout from the device
        if self.verbose:
            print("stdout from the device:")
            print(device_stdout)

        ep.disconnect()
        if ack == None:
            print("Xscope host received no response from device")
            print(f"device stdout: {device_stdout}")
            assert False
        return device_stdout


    def xscope_controller_cmd_connect(self):
        """
        Run command to ensure that the xcore device is setup and ready to communicate via ethernet

        Returns:
        stdout and stderr from running the host application
        """
        return self.xscope_controller_do_command([XscopeControl.XscopeCommands['CMD_DEVICE_CONNECT'].value])


    def xscope_controller_cmd_shutdown(self):
        """
        Run command to shutdown the xcore application threads and exit gracefully

        Returns:
        stdout and stderr from running the host application
        """
        return self.xscope_controller_do_command([XscopeControl.XscopeCommands['CMD_DEVICE_SHUTDOWN'].value])

    def xscope_controller_cmd_set_dut_macaddr(self, client_index, mac_addr):
        """
        Run command to set the src mac address of a client running on the DUT.

        Parameters:
        client_index: index of the client.
        mac_addr: mac address (example, 11:e0:24:df:33:66)

        Returns:
        stdout and stderr from running the host application
        """
        mac_addr_bytes = [int(i, 16) for i in mac_addr.split(":")]
        cmd_plus_args = [XscopeControl.XscopeCommands['CMD_SET_DEVICE_MACADDR'].value, client_index]
        cmd_plus_args.extend(mac_addr_bytes)
        return self.xscope_controller_do_command(cmd_plus_args)

    def xscope_controller_cmd_set_host_macaddr(self, mac_addr):
        """
        Run command to inform the DUT of the host's mac address. This is required so that a TX client running on the DUT knows the destination
        mac address for the ethernet packets it is sending.

        Parameters:
        mac_addr: mac address (example, 11:e0:24:df:33:66)

        Returns:
        stdout and stderr from running the host application
        """
        mac_addr_bytes = [int(i, 16) for i in mac_addr.split(":")]
        cmd_plus_args = [XscopeControl.XscopeCommands['CMD_SET_HOST_MACADDR'].value]
        cmd_plus_args.extend(mac_addr_bytes)
        return self.xscope_controller_do_command(cmd_plus_args)

    def xscope_controller_cmd_set_dut_tx_packets(self, client_index, arg1, arg2):
        """
        Run command to inform the TX clients on the DUT the number of packets and length of each packet that it needs to transmit

        Parameters:
        arg1: number of packets to send for LP thread. qav bw in bps for HP thread
        arg2: packet payload length in bytes

        Returns:
        stdout and stderr from running the host application
        """
        cmd_plus_args = [XscopeControl.XscopeCommands['CMD_HOST_SET_DUT_TX_PACKETS'].value]
        for a in [client_index, arg1, arg2]: # client_index, arg1 and arg2 are int32
            bytes_to_append = [(a >> (8 * i)) & 0xFF for i in range(4)]
            cmd_plus_args.extend(bytes_to_append)
        return self.xscope_controller_do_command(cmd_plus_args)


    def xscope_controller_cmd_set_dut_receive(self, client_index, recv_flag):
        """
        Run command to a given RX client on the DUT to start or stop receiving packets.

        Parameters:
        client_index: RX client index on the DUT
        recv_flag: Flag indicating whether to receive (1) or not receive (0) the packet

        Returns:
        stdout and stderr from running the host application
        """
        cmd_plus_args = [XscopeControl.XscopeCommands['CMD_SET_DUT_RECEIVE'].value, client_index, recv_flag]
        return self.xscope_controller_do_command(cmd_plus_args)

    def xscope_controller_cmd_restart_dut_mac(self):
        """
        Run command to restart the DUT Mac.

        Returns:
        stdout and stderr from running the host application
        """
        return self.xscope_controller_do_command([XscopeControl.XscopeCommands['CMD_EXIT_DEVICE_MAC'].value])

class XcoreAppControl(XcoreApp):
    """
    Class containing host side functions used for communicating with the XMOS device (DUT) over xscope port.
    These are wrapper functions that run the C++ xscope host application which actually communicates with the DUT over xscope.
    It is derived from XcoreApp which xruns the DUT application with the --xscope-port option.
    """
    def __init__(self, adapter_id, xe_name, attach=None, verbose=False):
        """
        Initialise the XcoreAppControl class. This compiles the xscope host application (host/xscope_controller).
        It also calls init for the base class XcoreApp, which xruns the XMOS device application (DUT) such that the host app
        can communicate to it over xscope port

        Parameter: compiled DUT application binary
        adapter-id: adapter ID of the XMOS device
        """
        self.verbose = verbose
        assert platform.system() in ["Darwin", "Linux"]
        super().__init__(xe_name, adapter_id, attach=attach)
        assert self.attach == "xscope_app"
        self.xscope_host = None

    def __enter__(self):
        super().__enter__()
        # self.xscope_port is only set in XcoreApp.__enter__(), so xscope_host can only be created here and not in XcoreAppControl's constructor
        self.xscope_host = XscopeControl("localhost", f"{self.xscope_port}", verbose=self.verbose)
        return self

"""
Do not change the main function since it's called from CMakeLists.txt to autogenerate the xscope commands enum .h file
"""
if __name__ == "__main__":
    print("Generate xscope cmds enum .h file")
    assert len(sys.argv) == 2, ("Error: filename not provided" +
                    "\nUsage: python generate_xscope_cmds_enum_h_file.py <.h file name, eg. enum.h>\n")

    XscopeControl.XscopeCommands.write_to_h_file(sys.argv[1])
