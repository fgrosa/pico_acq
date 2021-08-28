#!/usr/bin/env python3

'''Utils methods to generate and read a signal with the picospe 6000a driver device
'''

import ctypes
import string
import numpy as np
from picosdk.ps6000a import ps6000a as ps
from picosdk.PicoDeviceEnums import picoEnum as enums
from picosdk.PicoDeviceStructs import picoStruct as structs
from picosdk.functions import adc2mV, mV2adc, assert_pico_ok

# for some reasons there is no PICO_CONNECT_PROBE_RANGE in picoEnum
PICO_CONNECT_PROBE_RANGE = {
    'PICO_10MV': 0,
    'PICO_20MV': 1,
    'PICO_50MV': 2,
    'PICO_100MV': 3,
    'PICO_200MV': 4,
    'PICO_500MV': 5,
    'PICO_1V': 6,
    'PICO_2V': 7,
    'PICO_5V': 8,
    'PICO_10V': 9,
    'PICO_20V': 10
}

def turnon_readout_channel_DC(status, handle, channel_names, channel_ranges, channel_couplings, **kwargs):
    '''
    Method to turn on a channel for DC readout
    '''

    # check if it is a single channel instead of a list
    if not isinstance(channel_names, list):
        channel_names = [channel_names]

    # Set channels on
    channels_on = {}
    for channel_name, channel_range, channel_coupling in zip(channel_names, channel_ranges, channel_couplings):
        channels_on[channel_name] = enums.PICO_CHANNEL[f'PICO_CHANNEL_{channel_name}']
        coupling = enums.PICO_COUPLING[channel_coupling]
        channel_range = PICO_CONNECT_PROBE_RANGE[channel_range]
        bandwidth = enums.PICO_BANDWIDTH_LIMITER['PICO_BW_FULL']
        status[f'setChannel{channel_name}'] = ps.ps6000aSetChannelOn(
            handle,
            channels_on[channel_name],
            coupling,
            channel_range,
            0,  # analogueOffset = 0 V
            bandwidth
        )
        assert_pico_ok(status[f'setChannel{channel_name}'])

    # set other channels off
    for ch in list(string.ascii_uppercase)[:8]:
        if ch not in channel_names:
            channel = enums.PICO_CHANNEL[f'PICO_CHANNEL_{ch}']
            status['setChannel', channel] = ps.ps6000aSetChannelOff(handle, channel)
            assert_pico_ok(status['setChannel', channel])

    return channels_on


def generate_signal(status, handle, func='PICO_SINE', **kwargs):
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
    status['sigGenWaveform'] = ps.ps6000aSigGenWaveform(
        handle,
        wavetype,
        ctypes.byref(buffer),
        buffer_length
    )
    assert_pico_ok(status['sigGenWaveform'])

    # Set signal generator range
    status['sigGenRange'] = ps.ps6000aSigGenRange(handle, peak_to_peak_volts, offset_volts)
    assert_pico_ok(status['sigGenRange'])

    # Set signal generator duty cycle
    status['sigGenDutyCycle'] = ps.ps6000aSigGenWaveformDutyCycle(handle, duty_cycle_percent)
    assert_pico_ok(status['sigGenDutyCycle'])

    # Set signal generator frequency
    status['sigGenFreq'] = ps.ps6000aSigGenFrequency(handle, frequency_hz)
    assert_pico_ok(status['sigGenFreq'])

    # Set signal generator trigger event
    status['sigGenTrigger'] = ps.ps6000aSigGenTrigger(
        handle,
        enums.PICO_SIGGEN_TRIG_TYPE['PICO_SIGGEN_RISING'],
        enums.PICO_SIGGEN_TRIG_SOURCE['PICO_SIGGEN_SCOPE_TRIG'],
        1, # only play a single cycle
        0 # no auto-trigger
    )
    assert_pico_ok(status['sigGenTrigger'])
    
    # Apply signal generator settings
    sig_gen_enabled = 1
    sweep_enabled = 0
    trigger_enabled = 1
    auto_clock_opt_enabled = 0
    override_auto_clock_and_prescale = 0
    frequency = ctypes.c_int16(frequency_hz)
    status['sigGenApply'] = ps.ps6000aSigGenApply(
        handle,
        sig_gen_enabled,
        sweep_enabled,
        trigger_enabled,
        auto_clock_opt_enabled,
        override_auto_clock_and_prescale,
        ctypes.byref(frequency),
        None,  # stop_frequency
        None,  # frequency_increment
        None   # dwell_time
    )
    assert_pico_ok(status['sigGenApply'])

def set_simple_trigger(status, handle, source, trigger_thrs_mV, resolution, channel_range, direction = 'RISING_OR_FALLING', dummy = False):
    '''
    Method to setup a trigger
    '''
    
    # get max ADC value
    min_ADC = ctypes.c_int16()
    max_ADC = ctypes.c_int16()
    status['getAdcLimits'] = ps.ps6000aGetAdcLimits(
        handle,
        resolution,
        ctypes.byref(min_ADC),
        ctypes.byref(max_ADC)
    )
    assert_pico_ok(status['getAdcLimits'])

    # set simple trigger
    pico_direction = enums.PICO_THRESHOLD_DIRECTION[direction]
    pico_channel_range = PICO_CONNECT_PROBE_RANGE[channel_range]

    status['setSimpleTrigger'] = ps.ps6000aSetSimpleTrigger(
        handle,
        0 if dummy else 1,
        source,
        mV2adc(trigger_thrs_mV, pico_channel_range, max_ADC),
        pico_direction,
        0,  # delay = 0 s
        1000000  # autoTriggerMicroSeconds
    )
    assert_pico_ok(status['setSimpleTrigger'])


def read_channel_streaming(status, handle, resolution, sources, **kwargs):
    '''
    Method to read out a signal with given source channels using the straming functionality
    '''

    n_pretrigger_samples = kwargs.get('n_pretrigger_samples', 1000)
    n_posttrigger_samples = kwargs.get('n_posttrigger_samples', 9000)
    sample_interval = kwargs.get('sample_interval', 1)
    time_units = kwargs.get('time_units', 'NS')
    range_V = kwargs.get('range_V', '10MV')

    # set number of samples to be collected
    n_samples = n_pretrigger_samples + n_posttrigger_samples

    # set data buffer
    buffer = {}
    for i_source, source in enumerate(sources.items()):
        buffer[source[0]] = (ctypes.c_int16 * n_samples)()
        data_type = enums.PICO_DATA_TYPE['PICO_INT16_T']
        waveform = 0
        downsample_ratio_mode = enums.PICO_RATIO_MODE['PICO_RATIO_MODE_RAW']
        clear = enums.PICO_ACTION['PICO_CLEAR_ALL']
        add = enums.PICO_ACTION['PICO_ADD']
        if i_source == 0:
            action = clear|add
        else:
            action = add
        status['setDataBuffer'] = ps.ps6000aSetDataBuffer(
            handle,
            source[1],
            ctypes.byref(buffer[source[0]]),
            n_samples,
            data_type,
            waveform,
            downsample_ratio_mode,
            action
        )
        assert_pico_ok(status['setDataBuffer'])

    # run streaming capture
    time_units_pico = enums.PICO_TIME_UNITS[f'PICO_{time_units}']
    sample_interval_pico = ctypes.c_double(sample_interval)
    auto_stop = 1 # stop once buffer is full
    status['runStreaming'] = ps.ps6000aRunStreaming(
        handle,
        ctypes.byref(sample_interval_pico),
        time_units_pico,
        n_pretrigger_samples,
        n_posttrigger_samples,
        auto_stop,
        1,  # downSampleRatio
        downsample_ratio_mode
    )
    assert_pico_ok(status['runStreaming'])

    # get max ADC value
    min_ADC = ctypes.c_int16()
    max_ADC = ctypes.c_int16()
    status['getAdcLimits'] = ps.ps6000aGetAdcLimits(
        handle,
        resolution,
        ctypes.byref(min_ADC),
        ctypes.byref(max_ADC)
    )
    assert_pico_ok(status['getAdcLimits'])

    time_unit_mult_fact = 1.
    if time_units == 'S':
        time_unit_mult_fact = 1.e+9
    elif time_units == 'MS':
        time_unit_mult_fact = 1.e+6
    elif time_units == 'US':
        time_unit_mult_fact = 1.e+3
    elif time_units == 'PS':
        time_unit_mult_fact = 1.e-3
    elif time_units == 'FS':
        time_unit_mult_fact = 1.e-6

    # create time data
    time = np.linspace(0, n_samples * sample_interval * time_unit_mult_fact, n_samples)  # ns

    # get data from scope
    adc2mV_chmax = {}
    channel_range = PICO_CONNECT_PROBE_RANGE[f'PICO_{range_V}'] # FIXME
    data_type = enums.PICO_DATA_TYPE['PICO_INT16_T']
    streaming_data_info = []
    streaming_data_info = (structs.PICO_STREAMING_DATA_INFO * len(sources))()
    for i_source, source in enumerate(sources.items()):
        streaming_data_info[i_source].bufferIndex = 0
        streaming_data_info[i_source].channel = source[1]
        streaming_data_info[i_source].mode = downsample_ratio_mode
        streaming_data_info[i_source].noOfSamples = 0
        streaming_data_info[i_source].overflow = 0
        streaming_data_info[i_source].startIndex = 0
        streaming_data_info[i_source].type = data_type

    trigger_info = structs.PICO_STREAMING_DATA_TRIGGER_INFO()
    trigger_info.triggerAt = 0
    trigger_info.triggered = 0
    trigger_info.autoStop = auto_stop

    status['getStreamingLatestValues'] = ps.ps6000aGetStreamingLatestValues(
        handle,
        ctypes.byref(streaming_data_info),
        len(sources),
        ctypes.byref(trigger_info)
    )
    assert_pico_ok(status['getStreamingLatestValues'])    
    
    # convert ADC counts data to mV
    for source in sources:
        adc2mV_chmax[source] = adc2mV(buffer[source], channel_range, max_ADC)

    return adc2mV_chmax, time

def sample_interval_ns2timebase(sample_interval_ns):
    if sample_interval_ns < 3.2:
        const = 5
        timebase = int(np.log2(sample_interval_ns * const))
    else:
        const = 156.25e-3
        timebase = int(sample_interval_ns * const + 4)

    return timebase

def timebase2sample_interval_ns(timebase):
    if timebase < 5:
        const = 5
        sample_interval_ns = np.power(2, timebase) / const
    else:
        const = 156.25e-3
        sample_interval_ns = (timebase - 4) / const

    return sample_interval_ns

def read_channel_runblock(status, handle, resolution, sources, source_ranges, sample_interval_ns, **kwargs):
    '''
    Method to read out a signal with a given source channel using the runBlock functionality
    '''

    n_pretrigger_samples = kwargs.get('n_pretrigger_samples', 10000)
    n_posttrigger_samples = kwargs.get('n_posttrigger_samples', 90000)

    if sample_interval_ns < 0:
        timebase = ctypes.c_uint32(0)
        sample_interval_s = ctypes.c_double(0)

        # use the fastest available timebase
        enabled_channel_flags = sum([enums.PICO_CHANNEL_FLAGS[f'PICO_CHANNEL_{channel_name}_FLAGS'] for channel_name in sources.keys()])
        status['getMinimumTimebaseStateless'] = ps.ps6000aGetMinimumTimebaseStateless(
            handle,
            enabled_channel_flags,
            ctypes.byref(timebase),
            ctypes.byref(sample_interval_s),
            resolution
        )
        
        timebase = timebase.value
        sample_interval_ns = sample_interval_s.value * 1e9
    else:
        # pick the timebase that's closest to the demanded value
        timebase = sample_interval_ns2timebase(sample_interval_ns)
        sample_interval_ns = timebase2sample_interval_ns(timebase)
        
    # set number of samples to be collected
    n_samples = n_pretrigger_samples + n_posttrigger_samples

    # Create buffers
    buffer_min = {}
    buffer_max = {}

    for ind, (source_name, source_handle) in enumerate(sources.items()):
    
        buffer_max[source_name] = (ctypes.c_int16 * n_samples)()
        buffer_min[source_name] = (ctypes.c_int16 * n_samples)() # used for downsampling which isn't in the scope of this example

        # set data buffers
        data_type = enums.PICO_DATA_TYPE['PICO_INT16_T']
        waveform = 0
        downsample_ratio_mode = enums.PICO_RATIO_MODE['PICO_RATIO_MODE_RAW']
        clear = enums.PICO_ACTION['PICO_CLEAR_ALL']
        add = enums.PICO_ACTION['PICO_ADD']
        action = clear|add if ind == 0 else add
        status['setDataBuffers'] = ps.ps6000aSetDataBuffers(
            handle,
            source_handle,
            ctypes.byref(buffer_max[source_name]),
            ctypes.byref(buffer_min[source_name]),
            n_samples,
            data_type,
            waveform,
            downsample_ratio_mode,
            action
        )
        assert_pico_ok(status['setDataBuffers'])
    
    # run block capture
    time_indisposed_ms = ctypes.c_double(0)
    status['runBlock'] = ps.ps6000aRunBlock(
        handle,
        n_pretrigger_samples,
        n_posttrigger_samples,
        timebase,
        ctypes.byref(time_indisposed_ms),
        0,  # segmentIndex
        None,  # lpReady = None   Using IsReady rather than a callback
        None  # pParameter
    )
    assert_pico_ok(status['runBlock'])

    # check for data collection to finish using ps6000aIsReady
    ready = ctypes.c_int16(0)
    check = ctypes.c_int16(0)
    while ready.value == check.value:
        status['isReady'] = ps.ps6000aIsReady(handle, ctypes.byref(ready))

    # get data from scope
    n_of_samples = ctypes.c_uint64(n_samples)
    overflow = ctypes.c_int16(0)
    status['getValues'] = ps.ps6000aGetValues(
        handle,
        0,  # startIndex
        ctypes.byref(n_of_samples),
        1,  # downSampleRatio
        downsample_ratio_mode,
        0,  # segmentIndex
        ctypes.byref(overflow)
    )
    assert_pico_ok(status['getValues'])

    # get max ADC value
    min_ADC = ctypes.c_int16()
    max_ADC = ctypes.c_int16()
    status['getAdcLimits'] = ps.ps6000aGetAdcLimits(
        handle,
        resolution,
        ctypes.byref(min_ADC),
        ctypes.byref(max_ADC)
    )
    assert_pico_ok(status['getAdcLimits'])

    # convert ADC counts data to mV
    waveform_mV = {}

    for source_name in sources.keys():
        cur_source_range = source_ranges[source_name]
        cur_channel_range = PICO_CONNECT_PROBE_RANGE[cur_source_range]
        waveform_mV[source_name] = adc2mV(buffer_max[source_name], cur_channel_range, max_ADC)

    # create time data
    time = np.linspace(0, (n_samples - 1) * sample_interval_ns, n_samples)

    return waveform_mV, time
