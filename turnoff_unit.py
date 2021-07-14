#!/usr/bin/env python3

'''
Script to close picoscopue unit when it gets stuck
'''

import argparse
import ctypes
from picosdk.ps6000a import ps6000a as ps
from picosdk.PicoDeviceEnums import picoEnum as enums
import matplotlib.pyplot as plt
from picosdk.functions import assert_pico_ok

from utils import turnon_readout_channel_DC, generate_signal, read_channel_DC

parser = argparse.ArgumentParser(description='Arguments')
parser.add_argument('--channel', metavar='text', default='A', help='channel for readout')
args = parser.parse_args()

# Create chandle and status ready for use
chandle = ctypes.c_int16()
status = {}

# Open 6000 A series PicoScope
# returns handle to chandle for use in API functions
resolution = enums.PICO_DEVICE_RESOLUTION['PICO_DR_8BIT']
status['openunit'] = ps.ps6000aOpenUnit(ctypes.byref(chandle), None, resolution)
assert_pico_ok(status['openunit'])

# Close the scope
status['closeunit'] = ps.ps6000aCloseUnit(chandle)
assert_pico_ok(status['closeunit'])

print(status)