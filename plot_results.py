#!/usr/bin/env python3

'''
Script to plot results
'''

import argparse, os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import yaml

parser = argparse.ArgumentParser(description='Arguments')
parser.add_argument('config', metavar='text', default='config_plot.yml', help='input yaml config file')
args = parser.parse_args()

with open(args.config, 'r') as yml_config:
    input_cfg = yaml.load(yml_config, yaml.FullLoader)
infiles = input_cfg['infiles']
leg_names = input_cfg['legnames']
tmin = input_cfg['range']['tmin']
tmax = input_cfg['range']['tmax']
Vmin = input_cfg['range']['Vmin']
Vmax = input_cfg['range']['Vmax']
outfile = input_cfg['outfile']

fig = plt.figure(figsize=(8, 8))
for infile, leg_name in zip(infiles, leg_names):
    if '.dat' in infile or '.csv' in infile or '.txt' in infile:
        df = pd.read_csv(infile, sep=' ', names=('time', 'signal'))
    elif '.parquet' in infile:
        df = pd.read_parquet(infile)
    plt.plot(df['time'].to_numpy(), df['signal'].to_numpy(), label=leg_name, alpha=0.5)
plt.xlabel('time (ns)')
plt.ylabel('voltage (mV)')

print(f'\nDeltat = {(df["time"].to_numpy()[1]-df["time"].to_numpy()[0]):.2f} ns\n')

if tmin != None and tmax != None:
    plt.xlim(tmin, tmax)
if Vmin != None and Vmax != None:
    plt.ylim(Vmin, Vmax)

plt.legend(loc='best', ncol=2)

df = pd.read_parquet(args.infile)
fig = plt.figure(figsize=(10, 10))
plt.plot(df['time'].to_numpy(), df['signal'].to_numpy())
plt.xlabel('time (ns)')
plt.ylabel('voltage (mV)')
plt.savefig(outfile)
plt.close()
plt.show()
