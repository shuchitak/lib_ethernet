# Copyright 2014-2024 XMOS LIMITED.
# This Software is subject to the terms of the XMOS Public Licence: Version 1.
import Pyxsim as px
import sys
import zlib

class Clock(px.SimThread):

    # Use the values that need to be presented in the RGMII data pins when DV inactive
    (CLK_125MHz, CLK_25MHz, CLK_2_5MHz) = (0x4, 0x2, 0x0)

    def __init__(self, port, clk):
        self._running = True
        self._clk = clk
        if clk == self.CLK_125MHz:
            self._period = float(1000000000) / 125000000
            self._name = '125Mhz'
            self._min_ifg = 96
            self._bit_time = 1
        elif clk == self.CLK_25MHz:
            self._period = float(1000000000) / 25000000
            self._name = '25Mhz'
            self._bit_time = 10
        elif clk == self.CLK_2_5MHz:
            self._period = float(1000000000) / 2500000
            self._name = '2.5Mhz'
            self._bit_time = 100
        self._min_ifg = 96 * self._bit_time
        self._val = 0
        self._port = port

    def run(self):
        while True:
            self.wait_until(self.xsi.get_time() + self._period/2)
            self._val = 1 - self._val

            if self._running:
                self.xsi.drive_port_pins(self._port, self._val)

    def is_high(self):
        return (self._val == 1)

    def is_low(self):
        return (self._val == 0)

    def get_rate(self):
        return self._clk

    def get_name(self):
        return self._name

    def get_min_ifg(self):
        return self._min_ifg

    def get_bit_time(self):
        return self._bit_time

    def stop(self):
        self._running = False

    def start(self):
        self._running = True
