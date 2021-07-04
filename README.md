# PICOSCOPE Data Acquisition
Data acquisition with PICOSCOPE 6000a driver device using python API

## SDK and python API installation
- Install Picoscope 6000 series software from [https://www.picotech.com/downloads](https://www.picotech.com/downloads)
### Make python API work on macOS - based on [Making_the_Python_wrappers_work](https://www.element14.com/community/roadTestReviews/2856/l/picoscope-5444d-mso-usb-oscilloscope-review#jive_content_id_Making_the_Python_wrappers_work)
- Step 1) clone [picosdk-python-wrappers](https://github.com/picotech/picosdk-python-wrappers.git)
```bash
git clone https://github.com/picotech/picosdk-python-wrappers.git
```
- Step 2) in order to include the library in `DYLD_LIBRARY_PATH` edit the `picosdk-python-wrappers/picosdk/library.py` file adding the following lines at the end of the import section
```py
# Set DYLD_LIBRARY_PATH  
import os  
from sys import platform  
if platform == "darwin":  
    os.environ["DYLD_LIBRARY_PATH"] = os.environ["LSST_LIBRARY_PATH"]  
```
- Step 3) install the wrapper
```bash
cd picosdk-python-wrappers
python3 setup.py install --user
```
- Step 4) copy the libraries from `/Applications/PicoScope\ 6.app/Contents/Resources/lib/` to another location, e.g. the `lib` directory in this repository
```bash
cp /Applications/PicoScope\ 6.app/Contents/Resources/lib/libps6000a.dylib path_to_this_repo/pico_acq/lib/
cp /Applications/PicoScope\ 6.app/Contents/Resources/lib/libps6000a.2.dylib path_to_this_repo/pico_acq/lib/
cp /Applications/PicoScope\ 6.app/Contents/Resources/lib/libiomp5.dylib path_to_this_repo/pico_acq/lib/
cp /Applications/PicoScope\ 6.app/Contents/Resources/lib/libpicoipp.1.dylib path_to_this_repo/pico_acq/lib/
```
- Step 5) make path changes to the libraries
```bash
sudo install_name_tool -add_rpath path_to_this_repo/pico_acq/lib/ path_to_this_repo/pico_acq/lib/libps6000a.dylib
sudo install_name_tool -add_rpath path_to_this_repo/pico_acq/lib/ path_to_this_repo/pico_acq/lib/libps6000a.2.dylib
sudo install_name_tool -change libiomp5.dylib path_to_this_repo/lib/libiomp5.dylib path_to_this_repo/lib/libpicoipp.1.dylib
```
- Step 6) add the library folder to the `LSST_LIBRARY_PATH` environment variable to `.bash_profile`
```bash
# PicoScope
export LSST_LIBRARY_PATH="path_to_this_repo/pico_acq/lib:$LSST_LIBRARY_PATH"
```
Repeat steps 4) - 6) for each series you are interested in.
## Run basic example
To run a basic example that generates a wave function and reads out te signal:
- connect the Picoscope to your laptop via the blue USB cable
- connect the AWG waveform generator (backside of the Picoscope) to channel A with a coaxial cable
- run the `simple_gen_read.py` script
```bash
python3 simple_gen_read.py [-h] [--channel text] [--func text] [--ampl AMPL] [--freq FREQ] [--offset OFFSET] [--outfile text] [--batch]
```
where the optional arguments are
```bash
  -h, --help       show this help message and exit
  --channel text   channel for readout
  --func text      generated function
  --ampl AMPL      peak-to-peak amplitude in V
  --freq FREQ      frequency in Hz
  --offset OFFSET  offset in V
  --outfile text   pdf output file
  --batch          suppress video output
```
