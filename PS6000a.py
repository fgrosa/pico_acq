import ctypes
from picosdk.ps6000a import ps6000a as ps
from picosdk.PicoDeviceEnums import picoEnum as enums
from picosdk.functions import assert_pico_ok

from .utils import (
    turnon_readout_channel_DC,
    compose_trigger_DNF,
    trigger_condition_on_channel,
    read_channel_streaming,
    read_channel_runblock,
    read_channel_rapidblock
)

class PS6000a:

    def __init__(self):

        # Create handle and status ready for use
        self.handle = ctypes.c_int16()
        self.status = {}

        # Open 6000 A series PicoScope
        # returns handle to handle for use in API functions
        self.resolution = enums.PICO_DEVICE_RESOLUTION['PICO_DR_10BIT']
        self.status['openunit'] = ps.ps6000aOpenUnit(ctypes.byref(self.handle), None, self.resolution)
        assert_pico_ok(self.status['openunit'])

    def __del__(self):
        self.status['stop'] = ps.ps6000aStop(self.handle)
        
    def activate_channels(self, channels_on, channel_ranges, channel_couplings):

        self.readout_channels = turnon_readout_channel_DC(
            self.status,
            self.handle,
            channels_on,
            channel_ranges,
            channel_couplings
        )

        # keep track of the channel settings
        self.channel_ranges = {channel_name: channel_range for channel_name, channel_range in zip(channels_on, channel_ranges)}
        self.channel_couplings = {channel_name: channel_coupling for channel_name, channel_coupling in zip(channels_on, channel_couplings)}

        return self.readout_channels
        
    def set_coincidence_trigger(self, channels, thresholds_mV, directions, autoTriggerMicroSeconds = 0):
        
        trigs = []
        for channel, threshold_mV, direction in zip(channels, thresholds_mV, directions):
            cur_trig = trigger_condition_on_channel(self.status, self.handle, self.resolution, 
                                                    channel = f'PICO_CHANNEL_{channel}',
                                                    channel_range = self.channel_ranges[channel],
                                                    trigger_thrs_mV = threshold_mV,
                                                    threshold_direction = direction
            )
            trigs.append(cur_trig)

        # build a simple AND
        compose_trigger_DNF(self.status, self.handle, conjunction_0 = trigs, autoTriggerMicroSeconds = autoTriggerMicroSeconds)

    def set_simple_trigger(self, threshold_mV, direction, channel = "A", autoTriggerMicroSeconds = 0):

        self.set_coincidence_trigger(channels = [channel], thresholds_mV = [threshold_mV], directions = [direction],
                                     autoTriggerMicroSeconds = autoTriggerMicroSeconds)

    def acquire(self, sample_interval_ns, mode = 'runBlock', **kwargs):
        
        if mode == 'runStreaming':
            sig, time = read_channel_streaming(
                self.status,
                self.handle,
                self.resolution,
                self.readout_channels,
                n_pretrigger_samples=kwargs["n_pretrigger_samples"],
                n_posttrigger_samples=kwargs["n_posttrigger_samples"],
                sample_interval=2,
                time_units='NS',
                range_V = '10MV'
            )
        elif mode == 'runBlock':
            sig, time = read_channel_runblock(
                self.status, 
                self.handle,
                self.resolution,
                sources = self.readout_channels,
                source_ranges = self.channel_ranges,
                sample_interval_ns = sample_interval_ns,
                n_pretrigger_samples=kwargs["n_pretrigger_samples"],
                n_posttrigger_samples=kwargs["n_posttrigger_samples"]
            )
        elif mode == 'rapidBlock':
            sig, time = read_channel_rapidblock(
                self.status,
                self.handle,
                self.resolution,
                sources = self.readout_channels,
                source_ranges = self.channel_ranges,
                sample_interval_ns = sample_interval_ns,
                number_segments = kwargs.get("number_segments", 1),
                acq_window_ns = kwargs.get("acq_window_ns")
            )
        else:
            raise NotImplementedError(f'Mode {mode} unknown!')

        return sig, time
