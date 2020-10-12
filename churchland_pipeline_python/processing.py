import datajoint as dj
import re, inspect
from . import acquisition, equipment
from .utilities import datasync, datajointutils as dju
from brpylib import NsxFile, brpylib_ver
import math, numpy as np
from scipy import signal

schema = dj.schema('churchland_analyses_processing')

# -------------------------------------------------------------------------------------------------------------------------------
# LEVEL 0
# -------------------------------------------------------------------------------------------------------------------------------

@schema
class Filter(dj.Lookup):
    definition = """
    # Filter bank
    filter_id: int unsigned # unique filter identifier
    """
    
    class Beta(dj.Part):
        definition = """
        # Beta kernel
        -> master
        ---
        duration = 0.275: decimal(5,5) unsigned # interval kernel is defined over (s)
        alpha = 3: decimal(5,4) unsigned # shape parameter
        beta = 5: decimal(5,4) unsigned # shape parameter
        """ 

        def filter(self, y, fs, axis=0, normalize=False):

            assert len(self) == 1, 'Specify one filter'

            # convert parameters based on sample rate
            precision = int(np.ceil(np.log10(fs)))
            x = np.arange(0, float(self.fetch1('duration')), 1/fs).round(precision)

            # impulse response
            a = float(self.fetch1('alpha'))
            b = float(self.fetch1('beta'))
            B = (math.gamma(a)*math.gamma(b))/math.gamma(a+b)
            fx = (x**(a-1) * (1-x)**(b-1))/B

            # filter input
            z = signal.fftconvolve(y, fx, mode='same', axes=axis)

            # normalize by magnitude of impule response
            if normalize:
                z /= fx.max()

            return z
        

    class Boxcar(dj.Part):
        definition = """
        -> master
        ---
        duration = 0.1: decimal(18,9) unsigned # filter duration (s)
        """

        def filter(self, y, fs, axis=0, normalize=False):

            assert len(self) == 1, 'Specify one filter'

            # convert parameters based on sample rate
            wid = int(round(fs * float(self.fetch1('duration'))))
            half_wid = int(np.ceil(wid/2))

            # impulse response
            fx = np.concatenate((np.zeros(half_wid), np.ones(wid), np.zeros(half_wid)))

            # filter input
            z = signal.fftconvolve(y, fx, mode='same', axes=axis)

            # normalize by magnitude of impule response
            if normalize:
                z /= fx.max()

            return z
    

    class Butterworth(dj.Part):
        definition = """
        -> master
        ---
        order = 2: tinyint unsigned # filter order
        low_cut = 500: smallint unsigned # low-cut frequency (Hz)
        high_cut = null: smallint unsigned # high-cut frequency (Hz)
        """

        def filter(self, y, fs, axis=0):

            assert len(self) == 1, 'Specify one filter'

            # parse inputs
            n, low_cut, high_cut = self.fetch1('order','low_cut','high_cut')
            
            assert low_cut or high_cut, 'Missing critical frequency or frequencies'

            if low_cut and high_cut:
                btype = 'bandpass'
                Wn = [low_cut, high_cut]

            elif low_cut and not high_cut:
                btype = 'highpass'
                Wn = low_cut

            else:
                btype = 'lowpass'
                Wn = high_cut

            # get second order sections
            sos = signal.butter(n, Wn, btype, fs=fs, output='sos')

            # filter input
            z = signal.sosfilt(sos, y, axis=axis)

            return z            
        

    class Gaussian(dj.Part):
        definition = """
        # Gaussian kernel
        -> master
        ---
        sd = 25e-3: decimal(18,9) unsigned # filter standard deviation (s)
        width = 4: tinyint unsigned # filter width (multiples of standard deviations)
        """

        def filter(self, y, fs, axis=0, normalize=False):

            assert len(self) == 1, 'Specify one filter'

            # convert parameters based on sample rate
            sd = fs * float(self.fetch1('sd'))
            wid = round(sd * self.fetch1('width'))

            # impulse response
            x = np.arange(-wid,wid)
            fx = 1/(sd*np.sqrt(2*np.pi)) * np.exp(-x**2/(2*sd**2))

            # filter input
            z = signal.fftconvolve(y, fx, mode='same', axes=axis)

            # normalize by magnitude of impule response
            if normalize:
                z /= fx.max()

            return z

        
@schema
class SyncBlock(dj.Imported):
    definition = """
    # Speedgoat sync blocks, decoded from ephys files
    -> acquisition.EphysRecording
    sync_block_start: int unsigned # sample index (ephys time base) corresponding to the beginning of the sync block
    ---
    sync_block_time: double # encoded simulation time (Speedgoat time base)
    """

    key_source = acquisition.EphysRecording \
        & (acquisition.EphysRecording.Channel & {'channel_label':'sync'})

    def make(self, key):

        # fetch sync signal
        nsx_path = (acquisition.EphysRecording & key).fetch1('ephys_file_path')
        nsx_file = NsxFile(nsx_path)

        sync_channel_id = (acquisition.EphysRecording.Channel & key & {'channel_label': 'sync'}).fetch1('channel_id')
        sync_channel = nsx_file.getdata(sync_channel_id)

        nsx_file.close()

        # parse sync signal
        sync_block = datasync.decodesyncsignal(sync_channel)

        # remove corrupted blocks
        sync_block = [block for block in sync_block if not block['corrupted']]

        # append ephys recording data
        block_key = [dict(**key, sync_block_start=block['start'], sync_block_time=block['time']) for block in sync_block]

        self.insert(block_key)

# -------------------------------------------------------------------------------------------------------------------------------
# LEVEL 1
# -------------------------------------------------------------------------------------------------------------------------------

@schema
class MotorUnit(dj.Imported):
    definition = """
    # Sorted motor unit
    -> acquisition.EmgChannelGroup
    motor_unit_id: smallint unsigned # unique unit ID
    ---
    -> equipment.Software
    motor_unit_session_spikes: longblob # array of spike indices
    """
        
    class Template(dj.Part):
        definition = """
        # Sorted spike templates
        -> master
        -> acquisition.EmgChannelGroup.Channel
        ---
        motor_unit_template: longblob # waveform template
        """


@schema
class Neuron(dj.Imported):
    definition = """
    # Sorted neuron
    -> acquisition.NeuralChannelGroup
    neuron_id: smallint unsigned # unique unit ID
    ---
    -> equipment.Software
    neuron_isolation: enum("single","multi") # neuron isolation quality (single- or multi-unit)
    neuron_session_spikes: longblob # array of spike indices
    """
        
    class Template(dj.Part):
        definition = """
        # Sorted spike templates
        -> master
        -> acquisition.NeuralChannelGroup.Channel
        ---
        neuron_template: longblob # waveform template
        """