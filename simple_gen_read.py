#!/usr/bin/env python3

'''
This example opens a 6000a driver device, sets up channel A that generates a sine wave and channels that reads it
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
parser.add_argument('--func', metavar='text', default='PICO_SINE', help='generated function')
parser.add_argument('--ampl', type=float, default=2., help='peak-to-peak amplitude in V')
parser.add_argument('--freq', type=int, default=1000, help='frequency in Hz')
parser.add_argument('--offset', type=float, default=0., help='offset in V')
parser.add_argument("--outfile", metavar='text', default='signal.pdf', help='pdf output file')
parser.add_argument("--batch", help="suppress video output", action="store_true")
args = parser.parse_args()

# Create chandle and status ready for use
chandle = ctypes.c_int16()
status = {}

# Open 6000 A series PicoScope
# returns handle to chandle for use in API functions
resolution = enums.PICO_DEVICE_RESOLUTION['PICO_DR_8BIT']
status['openunit'] = ps.ps6000aOpenUnit(ctypes.byref(chandle), None, resolution)
assert_pico_ok(status['openunit'])

# preapare channel A to read out signals
readout_channel = turnon_readout_channel_DC(status, chandle, args.channel)

# generate a sine waveform with 2 V of peak-to-peak amplitude and 0 offset using AWG
generate_signal(status, chandle, args.func,
                peak_to_peak_volts=args.ampl, offset_volts=args.offset, frequency_hz=args.freq)

# read out signal from channel
sig, time = read_channel_DC(status, chandle, resolution, readout_channel)

# plot data
fig = plt.figure(figsize=(10, 10))
plt.plot(time, sig)
plt.xlabel('time (ns)')
plt.ylabel('voltage (mV)')
if not args.batch:
    plt.show()
plt.savefig(args.outfile)

# Close the scope
status['closeunit'] = ps.ps6000aCloseUnit(chandle)
assert_pico_ok(status['closeunit'])

print(status)