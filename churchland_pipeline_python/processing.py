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

    # easy insert
    @classmethod
    def ezinsert(self, ftype, **kwargs):

        try:
            # filter part table
            filter_part = getattr(self, ftype)

            # read part table secondary attributes
            attributes = inspect.getmembers(filter_part, lambda a:not(inspect.isroutine(a)))
            table_def = [a for a in attributes if a[0].startswith('definition')][0][-1]
            table_def_lines = [s.lstrip() for s in table_def.split('\n')]

            attr_name = re.compile('\w+')
            attr_default = re.compile('\w+\s*=\s*(.*):')
            part_attr = {attr_name.match(s).group(0) : (float(attr_default.match(s).group(1)) if attr_default.match(s) else np.nan) \
                for s in table_def_lines if attr_name.match(s)}

            # ensure keyword keys are members of secondary attributes list
            assert set(kwargs.keys()).issubset(set(part_attr.keys())), 'Unrecognized keyword argument(s)'

            # check if entry already exists in table
            if filter_part():

                # append default values if missing
                for key,val in part_attr.items():
                    if key not in kwargs.keys():
                        kwargs.update({key:val})

                # existing entries
                filters = filter_part.fetch(as_dict=True)
                filter_attr = [{k:float(v) for k,v in filt.items() if k!='filter_id'} for filt in filters]
                
                # cross reference
                assert not any([kwargs == filt for filt in filter_attr]), 'Duplicate entry!'

            # get next filter ID
            if not(filter_part()):
                new_id = 0
            else:
                all_id = filter_part.fetch('filter_id')
                new_id = next(i for i in range(2+max(all_id)) if i not in all_id)

            filter_key = {'filter_id': new_id}

            # insert filter ID to master table
            if not self & filter_key:
                self.insert1(filter_key)

            # insert filter to part table
            filter_part.insert1(dict(**filter_key, **kwargs))

        except AttributeError:
            print('Unrecognized filter type: {}'.format(ftype))
        
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