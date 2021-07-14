#!/usr/bin/env python3

'''
Utils methods to generate and read a signal with the picospe 6000a driver device
'''

import ctypes
import string
import numpy as np
from picosdk.ps6000a import ps6000a as ps
from picosdk.PicoDeviceEnums import picoEnum as enums
from picosdk.functions import adc2mV, assert_pico_ok

def turnon_readout_channel_DC(status, chandle, channel_name='A'):
    '''
    Method to turn on a channel for DC readout
    '''
    # Set channel on
    channel_on = enums.PICO_CHANNEL[f'PICO_CHANNEL_{channel_name}']
    coupling = enums.PICO_COUPLING['PICO_DC']
    channelRange = 7
    # analogueOffset = 0 V
    bandwidth = enums.PICO_BANDWIDTH_LIMITER['PICO_BW_FULL']
    status[f'setChannel{channel_name}'] = ps.ps6000aSetChannelOn(chandle, channel_on, coupling,
                                                                 channelRange, 0, bandwidth)
    assert_pico_ok(status[f'setChannel{channel_name}'])

    # set other channels off
    for ch in list(string.ascii_uppercase)[:channelRange+1]:
        if ch != channel_name:
            channel = enums.PICO_CHANNEL[f'PICO_CHANNEL_{ch}']
            status['setChannel', channel] = ps.ps6000aSetChannelOff(chandle, channel)
            assert_pico_ok(status['setChannel', channel])

    return channel_on


def generate_signal(status, chandle, func='PICO_SINE', **kwargs):
    '''
    Method to generate a signal using the AWG
    '''

    peak_to_peak_volts = kwargs.get('peak_to_peak_volts', 2.)
    offset_volts = kwargs.get('offset_volts', 0.)
    frequency_hz = kwargs.get('frequency_hz', 10000)
    buffer_length = kwargs.get('buffer_length', 100000)
    duty_cycle_percent = kwargs.get('duty_cycle_percent', 50.)

    # Set signal generator waveform
    wavetype = enums.PICO_WAVE_TYPE[func]
    buffer = (ctypes.c_int16 * buffer_length)()
    status['sigGenWaveform'] = ps.ps6000aSigGenWaveform(chandle, wavetype, ctypes.byref(buffer), buffer_length)
    assert_pico_ok(status['sigGenWaveform'])

    # Set signal generator range
    status['sigGenRange'] = ps.ps6000aSigGenRange(chandle, peak_to_peak_volts, offset_volts)
    assert_pico_ok(status['sigGenRange'])

    # Set signal generator duty cycle
    status['sigGenDutyCycle'] = ps.ps6000aSigGenWaveformDutyCycle(chandle, duty_cycle_percent)
    assert_pico_ok(status['sigGenDutyCycle'])

    # Set signal generator frequency
    status['sigGenFreq'] = ps.ps6000aSigGenFrequency(chandle, frequency_hz)
    assert_pico_ok(status['sigGenFreq'])

    # Apply signal generator settings
    sig_gen_enabled = 1
    sweep_enabled = 0
    trigger_enabled = 0
    auto_clock_opt_enabled = 0
    override_auto_clock_and_prescale = 0
    frequency = ctypes.c_int16(frequency_hz)
    #stop_frequency = None
    #frequency_increment = None
    #dwell_time = None
    status['sigGenApply'] = ps.ps6000aSigGenApply(chandle,
                                                  sig_gen_enabled,
                                                  sweep_enabled,
                                                  trigger_enabled,
                                                  auto_clock_opt_enabled,
                                                  override_auto_clock_and_prescale,
                                                  ctypes.byref(frequency),
                                                  None,
                                                  None,
                                                  None)
    assert_pico_ok(status['sigGenApply'])


def read_channel_DC(status, chandle, resolution, source, **kwargs):
    '''
    Method to read out a signal with a given source channel
    '''

    n_pretrigger_samples = kwargs.get('n_pretrigger_samples', 500000)
    n_posttrigger_samples = kwargs.get('n_posttrigger_samples', 16000000)
    trigger_thrs = kwargs.get('trigger_thrs', 1000)

    # delay = 0 s
    # autoTriggerMicroSeconds = 1000000 us
    direction = enums.PICO_THRESHOLD_DIRECTION['PICO_RISING']
    status['setSimpleTrigger'] = ps.ps6000aSetSimpleTrigger(chandle, 1, source, trigger_thrs, direction, 0, 1000000)
    assert_pico_ok(status['setSimpleTrigger'])

    # Get fastest available timebase
    # handle = chandle
    enabledChannelFlags = enums.PICO_CHANNEL_FLAGS['PICO_CHANNEL_A_FLAGS']
    timebase = ctypes.c_uint32(0)
    timeInterval = ctypes.c_double(0)
    status['getMinimumTimebaseStateless'] = ps.ps6000aGetMinimumTimebaseStateless(chandle, enabledChannelFlags,
                                                                                  ctypes.byref(timebase),
                                                                                  ctypes.byref(timeInterval),
                                                                                  resolution)
    print(f'\n\033[92mtimebase = {timebase.value}')
    print(f'\033[92msample interval = {timeInterval.value} s\n')

    # Set number of samples to be collected
    n_samples = n_pretrigger_samples + n_posttrigger_samples

    # Create buffers
    buffer_max = (ctypes.c_int16 * n_samples)()
    buffer_min = (ctypes.c_int16 * n_samples)() # used for downsampling which isn't in the scope of this example

    # Set data buffers
    data_type = enums.PICO_DATA_TYPE['PICO_INT16_T']
    waveform = 0
    downsample_mode = enums.PICO_RATIO_MODE['PICO_RATIO_MODE_RAW']
    clear = enums.PICO_ACTION['PICO_CLEAR_ALL']
    add = enums.PICO_ACTION['PICO_ADD']
    action = clear|add
    status['setDataBuffers'] = ps.ps6000aSetDataBuffers(chandle, source, ctypes.byref(buffer_max),
                                                        ctypes.byref(buffer_min), n_samples, data_type,
                                                        waveform, downsample_mode, action)
    assert_pico_ok(status['setDataBuffers'])

    # Run block capture
    time_indisposed_ms = ctypes.c_double(0)
    # segmentIndex = 0
    # lpReady = None   Using IsReady rather than a callback
    # pParameter = None
    status['runBlock'] = ps.ps6000aRunBlock(chandle, n_pretrigger_samples, n_posttrigger_samples,
                                            timebase, ctypes.byref(time_indisposed_ms), 0, None, None)
    assert_pico_ok(status['runBlock'])

    # Check for data collection to finish using ps6000aIsReady
    ready = ctypes.c_int16(0)
    check = ctypes.c_int16(0)
    while ready.value == check.value:
        status['isReady'] = ps.ps6000aIsReady(chandle, ctypes.byref(ready))

    # Get data from scope
    # startIndex = 0
    n_of_samples = ctypes.c_uint64(n_samples)
    # downSampleRatio = 1
    # segmentIndex = 0
    overflow = ctypes.c_int16(0)
    status['getValues'] = ps.ps6000aGetValues(chandle, 0, ctypes.byref(n_of_samples), 1, downsample_mode, 0,
                                              ctypes.byref(overflow))
    assert_pico_ok(status['getValues'])

    # get max ADC value
    # handle = chandle
    minADC = ctypes.c_int16()
    maxADC = ctypes.c_int16()
    status['getAdcLimits'] = ps.ps6000aGetAdcLimits(chandle, resolution, ctypes.byref(minADC), ctypes.byref(maxADC))
    assert_pico_ok(status['getAdcLimits'])

    # convert ADC counts data to mV
    channelRange = 7
    adc2mVChAMax = adc2mV(buffer_max, channelRange, maxADC)

    # Create time data
    time = np.linspace(0, (n_samples) * timeInterval.value * 1000000000, n_samples)

    return adc2mVChAMax, time
