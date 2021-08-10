import ctypes
from picosdk.ps6000a import ps6000a as ps
from picosdk.PicoDeviceEnums import picoEnum as enums
from picosdk.functions import assert_pico_ok

from .utils import (
    turnon_readout_channel_DC,
    set_trigger,
    read_channel_streaming,
)

class PS6000a:

    def __init__(self):

        # Create chandle and status ready for use
        self.chandle = ctypes.c_int16()
        self.status = {}

        # Open 6000 A series PicoScope
        # returns handle to chandle for use in API functions
        self.resolution = enums.PICO_DEVICE_RESOLUTION['PICO_DR_10BIT']
        self.status['openunit'] = ps.ps6000aOpenUnit(ctypes.byref(self.chandle), None, self.resolution)
        assert_pico_ok(self.status['openunit'])

    def __del__(self):
        self.status['stop'] = ps.ps6000aStop(self.chandle)
        
    def activate_channels(self, channels_on):

        self.readout_channels = turnon_readout_channel_DC(
            self.status,
            self.chandle,
            channels_on,
            range_V = '10MV'
        )

    def set_dummy_trigger(self, channel = "A"):
        
        set_trigger(
            self.status,
            self.chandle,
            self.readout_channels[channel],
            -2000,
            'FALLING'
        )

    def acquire(self):
        
        sig, time = read_channel_streaming(
            self.status,
            self.chandle,
            self.resolution,
            self.readout_channels,
            n_pretrigger_samples=10000, # not triggering
            n_posttrigger_samples=10000, # not triggering
            sample_interval=2,
            time_units='NS',
            range_V = '50MV'
        )

        return sig, time
