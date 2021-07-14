#!/usr/bin/env python3

'''
Script to plot results
'''

import argparse
import pandas as pd
import matplotlib.pyplot as plt

parser = argparse.ArgumentParser(description='Arguments')
parser.add_argument("infile", metavar='text', default='signal.csv', help='txt input file')
args = parser.parse_args()

df = pd.read_csv(args.infile, sep=' ', names=('time', 'signal'))
fig = plt.figure(figsize=(10, 10))
plt.plot(time, sig)
plt.xlabel('time (ns)')
plt.ylabel('voltage (mV)')
plt.savefig(args.outfile)
plt.show()
