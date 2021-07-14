#!/usr/bin/env python3

'''
Readout signal from SPAD
'''

import argparse
import ctypes
import pandas as pd
from picosdk.ps6000a import ps6000a as ps
from picosdk.PicoDeviceEnums import picoEnum as enums
import matplotlib.pyplot as plt
from picosdk.functions import assert_pico_ok

from utils import turnon_readout_channel_DC, generate_signal, read_channel_DC

parser = argparse.ArgumentParser(description='Arguments')
parser.add_argument('--channel', metavar='text', default='A', help='channel for readout')
parser.add_argument('--npretrigger', type=int, default=500000, help='number of pre-trigger samples')
parser.add_argument('--nposttrigger', type=int, default=1600000, help='number of post-trigger samples')
parser.add_argument('--triggerthrs', type=int, default=-1000, help='trigger threshold (mV)')
parser.add_argument("--outfilePDF", metavar='text', default='signal.pdf', help='pdf output file')
parser.add_argument("--outfile", metavar='text', default='signal.csv', help='csv output file')
parser.add_argument("--saveoutput", help="save parquet file", action="store_true")
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

# preapare channel to read out signals
readout_channel = turnon_readout_channel_DC(status, chandle, args.channel)

# read out signal from channel
sig, time = read_channel_DC(status, chandle, resolution, readout_channel,
                            n_pretrigger_samples=args.npretrigger, n_posttrigger_samples=args.nposttrigger,
                            trigger_thrs=args.triggerthrs)

# Close the scope
status['closeunit'] = ps.ps6000aCloseUnit(chandle)
assert_pico_ok(status['closeunit'])

# plot data
if not args.batch:
    fig = plt.figure(figsize=(10, 10))
    plt.plot(time, sig)
    plt.xlabel('time (ns)')
    plt.ylabel('voltage (mV)')
    plt.savefig(args.outfile)
    plt.show()

# save the data
if args.saveoutput:
    print('\n\033[93mSaving output data ...', end='\r')
    df = pd.DataFrame({'time': time, 'signal': sig})
    df.to_csv(args.outfile, sep=' ', header=False, index=False)
    print('\033[92mSaving output data ... Done!\033[0m\n')
