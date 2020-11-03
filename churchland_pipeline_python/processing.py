import datajoint as dj
import os, re, inspect, math
import neo
import pandas as pd
import numpy as np
import scipy.io as sio
from . import acquisition, equipment, reference
from .utilities import datasync, datajointutils as dju
from scipy import signal

schema = dj.schema(dj.config.get('database.prefix') + 'churchland_analyses_processing')

# =======
# LEVEL 0
# =======

@schema
class BrainSort(dj.Manual):
    definition = """
    # Spike sorted brain data
    -> acquisition.BrainChannelGroup
    brain_sort_id: tinyint unsigned  # brain sort ID number
    ---
    -> equipment.Software
    brain_sort_path: varchar(1012)   # path to sort files
    """


@schema
class EmgSort(dj.Manual):
    definition = """
    # Spike sorted EMG data
    -> acquisition.EmgChannelGroup
    emg_sort_id: tinyint unsigned  # emg sort ID number
    ---
    -> equipment.Software
    emg_sort_path: varchar(1012)   # path to sort files
    """


@schema
class EmgChannelQuality(dj.Manual):
    definition = """
    -> acquisition.EmgChannelGroup.Channel
    ---
    emg_channel_quality: enum('sortable', 'unsortable', 'dead') # EMG channel quality
    """


@schema
class Filter(dj.Lookup):
    definition = """
    # Filter bank
    filter_id: int unsigned # filter ID number (for proper functionality, ensure uniqueness across all part tables)
    """
    
    class Beta(dj.Part):
        definition = """
        # Beta kernel
        -> master
        ---
        duration = 0.275: decimal(5,5) unsigned # distribution support interval (s)
        alpha = 3:        decimal(9,4) unsigned # shape parameter
        beta = 5:         decimal(9,4) unsigned # shape parameter
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
        order = 2:       tinyint unsigned  # filter order
        low_cut = 500:   smallint unsigned # low-cut frequency (Hz)
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
        width = 4:  tinyint unsigned       # filter width (multiples of sd)
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
    -> acquisition.EphysRecording.File
    sync_block_start: int unsigned # sample index (ephys time base) corresponding to the beginning of the sync block
    ---
    sync_block_time: double        # encoded simulation time (Speedgoat time base)
    """

    key_source = acquisition.EphysRecording.File \
        & (acquisition.EphysRecording.Channel & {'ephys_channel_type':'sync'})

    def make(self, key):

        # sync channel ID
        sync_rel = acquisition.EphysRecording.Channel & key & {'ephys_channel_type': 'sync'}
        sync_id, sync_idx = sync_rel.fetch1('ephys_channel_id', 'ephys_channel_idx')

        # fetch local ephys recording file path and sample rate
        fs_ephys, file_path, file_prefix, file_extension = (acquisition.EphysRecording * (acquisition.EphysRecording.File & key))\
            .fetch1('ephys_recording_sample_rate', 'ephys_recording_path', 'ephys_file_prefix', 'ephys_file_extension')

        ephys_file_path = (reference.EngramTier & {'engram_tier': 'locker'})\
            .ensurelocal(file_path + file_prefix + '.' + file_extension)

        # read NSx file
        reader = neo.rawio.BlackrockRawIO(ephys_file_path)
        reader.parse_header()

        # sync signal gain
        id_idx, gain_idx = [
            idx for idx, name in enumerate(reader.header['signal_channels'].dtype.names) \
            if name in ['id','gain']
        ]
        sync_gain = next(chan[gain_idx] for chan in reader.header['signal_channels'] if chan[id_idx]==sync_id)

        # extract NSx channel data from memory map (within a nested dictionary)
        nsx_data = next(iter(reader.nsx_datas.values()))
        nsx_data = next(iter(nsx_data.values()))

        # extract sync signal from NSx array and apply gain
        sync_signal = sync_gain * nsx_data[:, sync_idx]

        # parse sync signal
        sync_block = datasync.decodesyncsignal(sync_signal, fs_ephys)

        # remove corrupted blocks
        sync_block = [block for block in sync_block if not block['corrupted']]

        # append ephys recording data
        block_key = [dict(**key, sync_block_start=block['start'], sync_block_time=block['time']) for block in sync_block]

        self.insert(block_key)


# =======
# LEVEL 1
# =======

@schema
class MotorUnit(dj.Imported):
    definition = """
    # Sorted motor unit
    -> EmgSort
    motor_unit_id:            smallint unsigned # motor unit ID number
    ---
    motor_unit_spike_indices: longblob          # raw spike indices for the full recording
    """
        
    class Template(dj.Part):
        definition = """
        # Sorted spike templates
        -> master
        -> acquisition.EmgChannelGroup.Channel
        ---
        motor_unit_template: longblob # motor unit action potential waveform template
        """

    def make(self, key):

        # get path to sort files
        emg_sort = EmgSort & key
        emg_sort_path = emg_sort.fetch1('emg_sort_path')

        # load sort data
        if emg_sort & {'software': 'Myosort'}:

            # import last saved spike field
            spikes = sio.loadmat(emg_sort_path + 'spikes.mat')['Spk'][0][0][-1]

            # import labels and templates
            labels = sio.loadmat(emg_sort_path + 'labels.mat')['Lab'][0][0]
            templates = sio.loadmat(emg_sort_path + 'templates.mat')['W'][0][0]

            # infer import field based on last entry with non-zero templates
            import_idx = next(i for i in reversed(range(len(templates))) if templates[i].shape[0] > 0)
            import_field = templates.dtype.names[import_idx]

            labels = labels[next(i for i,name in enumerate(labels.dtype.names) if name==import_field)]
            templates = templates[import_idx]

            # label groups
            label_group = np.unique(labels)
            label_group = label_group[np.nonzero(label_group)]

        else:
            print('Spike sorter {} unrecognized. Unspecified import method.'.format(emg_sort.fetch1('software')))
            return None

        # //TODO add templates

        # construct motor unit keys
        motor_unit_key = [
            dict(**key, motor_unit_id=idx, motor_unit_spike_indices=spikes[labels == group])
            for idx, group in enumerate(label_group)
        ]

        # insert motor units
        self.insert(motor_unit_key)


@schema
class Neuron(dj.Imported):
    definition = """
    # Sorted brain neuron
    -> BrainSort
    neuron_id:            smallint unsigned       # neuron ID number
    ---
    neuron_isolation:     enum('single', 'multi') # neuron isolation quality (single- or multi-unit)
    neuron_spike_indices: longblob                # raw spike indices for the full recording
    """
        
    class Template(dj.Part):
        definition = """
        # Sorted spike templates
        -> master
        -> acquisition.BrainChannelGroup.Channel
        ---
        neuron_template: longblob # neuron action potential waveform template
        """

    def make(self, key):

        # get path to sort files
        brain_sort = BrainSort & key
        brain_sort_path = brain_sort.fetch1('brain_sort_path')

        # load sort data
        if brain_sort & {'software': 'Kilosort'}:
            
            t_spike = np.load(brain_sort_path + 'spike_times.npy')
            cluster_id = np.load(brain_sort_path + 'spike_clusters.npy')
            cluster_group = pd.read_csv(brain_sort_path + 'cluster_group.tsv', delimiter='\t')

            # rename cluster groups
            cluster_group['group'].replace({'good': 'single', 'mua': 'multi'}, inplace=True)

            # restrict neurons to single- or multi-units
            cluster_group = cluster_group[cluster_group['group'].isin(['single', 'multi'])]

        else:
            print('Spike sorter {} unrecognized. Unspecified import method.'.format(brain_sort.fetch1('software')))
            return None

        # construct neuron keys
        neuron_key = [
            dict(**key, neuron_id=idx, neuron_isolation=group, neuron_spike_indices=t_spike[cluster_id == clus])
            for idx, (clus, group) in enumerate(zip(cluster_group['cluster_id'], cluster_group['group']))
        ]

        # //TODO add templates (these will need to be reconstructed post-hoc, as the template IDs and cluster IDs
        # are not guaranteed to match after manual curation in Phy https://phy.readthedocs.io/en/latest/terminology/)

        # insert neurons
        self.insert(neuron_key)