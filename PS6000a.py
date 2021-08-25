import ctypes
from picosdk.ps6000a import ps6000a as ps
from picosdk.PicoDeviceEnums import picoEnum as enums
from picosdk.functions import assert_pico_ok

from .utils import (
    turnon_readout_channel_DC,
    set_trigger,
    read_channel_streaming,
    read_channel_runblock,
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
        
    def activate_channels(self, channels_on):

        self.readout_channels = turnon_readout_channel_DC(
            self.status,
            self.handle,
            channels_on,
            range_V = '10MV'
        )

    def set_trigger(self, threshold_mV, direction, channel = "A"):
        
        set_trigger(
            self.status,
            self.handle,
            self.readout_channels[channel],
            trigger_thrs_mV = threshold_mV,
            resolution = self.resolution,
            range_V = '10MV',
            direction = direction
        )

    def acquire(self, channel_name, n_pretrigger_samples, n_posttrigger_samples, mode = 'runStreaming'):
        
        if mode == 'runStreaming':
            sig, time = read_channel_streaming(
                self.status,
                self.handle,
                self.resolution,
                self.readout_channels,
                n_pretrigger_samples=n_pretrigger_samples,
                n_posttrigger_samples=n_posttrigger_samples,
                sample_interval=2,
                time_units='NS',
                range_V = '10MV'
            )
        elif mode == 'runBlock':
            sig, time = read_channel_runblock(
                self.status, 
                self.handle,
                self.resolution,
                self.readout_channels[channel_name],
                channel_name,
                n_pretrigger_samples=n_pretrigger_samples,
                n_posttrigger_samples=n_posttrigger_samples,
                range_V = '10MV'
            )
        else:
            raise NotImplementedError(f'Mode {mode} unknown!')

        return sig, time
