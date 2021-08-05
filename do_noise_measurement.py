#!/usr/bin/env python3

'''Perform noise measurement on SPAD
'''

import sys
import argparse
import ctypes
import pandas as pd
from picosdk.ps6000a import ps6000a as ps
from picosdk.PicoDeviceEnums import picoEnum as enums
from picosdk.functions import assert_pico_ok

from utils import (
    turnon_readout_channel_DC,
    set_trigger,
    read_channel_streaming,
)

# Create chandle and status ready for use
chandle = ctypes.c_int16()
status = {}

# Open 6000 A series PicoScope
# returns handle to chandle for use in API functions
resolution = enums.PICO_DEVICE_RESOLUTION['PICO_DR_10BIT']
status['openunit'] = ps.ps6000aOpenUnit(ctypes.byref(chandle), None, resolution)
assert_pico_ok(status['openunit'])

# preapare channel to read out signals
channels_on = ['A', 'B']
readout_channels = turnon_readout_channel_DC(
    status,
    chandle,
    channels_on,
    range_V = '50MV'
)

# set a trigger
set_trigger(
    status,
    chandle,
    readout_channels[channels_on[0]],
    -2000,
    'FALLING'
)

sig, time = read_channel_streaming(
    status,
    chandle,
    resolution,
    readout_channels,
    n_pretrigger_samples=10000, # not triggering
    n_posttrigger_samples=10000, # not triggering
    sample_interval=2,
    time_units='NS',
    range_V = '50MV'
)
print(sig)
# status['stop'] = ps.ps6000aStop(chandle)

