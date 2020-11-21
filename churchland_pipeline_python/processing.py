import datajoint as dj
import os, re, inspect, math, itertools
import neo
import pandas as pd
import numpy as np
import scipy.io as sio
import matplotlib.pyplot as plt
from . import acquisition, equipment, reference
from .utilities import datasync
from scipy import signal
from decimal import *

schema = dj.schema(dj.config.get('database.prefix') + 'churchland_common_processing')

# =======
# LEVEL 0
# =======

@schema
class BrainSort(dj.Manual):
    definition = """
    # Spike sorted brain data
    -> acquisition.BrainChannelGroup
    brain_sort_id: tinyint unsigned # brain sort ID number
    ---
    -> equipment.Software
    brain_sort_path: varchar(1012)  # path to sort files
    """


@schema
class EmgSort(dj.Manual):
    definition = """
    # Spike sorted EMG data
    -> acquisition.EmgChannelGroup
    emg_sort_id: tinyint unsigned # emg sort ID number
    ---
    -> equipment.Software
    emg_sort_path: varchar(1012)  # path to sort files
    """


@schema
class EphysChannelQuality(dj.Manual):
    definition = """
    -> acquisition.EphysRecording.Channel
    ---
    ephys_channel_quality: enum('sortable', 'unsortable', 'dead') # EMG channel quality
    """


@schema
class EphysSync(dj.Imported):
    definition = """
    # Ephys synchronization record with behavior
    -> acquisition.EphysRecording.File
    """

    # process recordings with sync signal
    key_source = acquisition.EphysRecording.File \
        & (acquisition.EphysRecording.Channel & {'ephys_channel_type':'sync'})

    class Block(dj.Part):
        definition = """
        # Behavior sync blocks, decoded from ephys files
        -> master
        sync_block_start: int unsigned # sample index (ephys time base) corresponding to the beginning of the sync block
        ---
        sync_block_time: double        # encoded simulation time (Speedgoat time base)
        """

    def make(self, key):

        # fetch sync channel index
        sync_idx = (acquisition.EphysRecording.Channel & key & {'ephys_channel_type': 'sync'}).fetch1('ephys_channel_idx')

        # fetch local ephys recording file path and sample rate
        fs_ephys = (acquisition.EphysRecording & key).fetch1('ephys_recording_sample_rate')
        ephys_file_path = (acquisition.EphysRecording.File & key).proj_file_path().fetch1('ephys_file_path')

        # ensure local path
        ephys_file_path = reference.EngramTier.ensure_local(ephys_file_path)

        # read NSx file
        reader = neo.rawio.BlackrockRawIO(ephys_file_path)
        reader.parse_header()

        # read and rescale sync signal
        raw_signal = reader.get_analogsignal_chunk(block_index=0, seg_index=0, channel_indexes=[sync_idx])
        sync_signal = reader.rescale_signal_raw_to_float(raw_signal, dtype='float64', channel_indexes=[sync_idx]).flatten()

        # parse sync signal
        sync_blocks = datasync.decode_sync_signal(sync_signal, fs_ephys)

        # append ephys recording data
        block_keys = [dict(key, sync_block_start=block['start'], sync_block_time=block['time']) for block in sync_blocks]

        # insert sync record
        self.insert1(key)

        # insert sync blocks
        self.Block.insert(block_keys)


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

        def filt(
            self, 
            y: np.ndarray, 
            fs: int, 
            duration: float=None,
            alpha: float=None,
            beta: float=None,
            axis: int=0, 
            normalize: bool=False
            ) -> np.ndarray:
            """Filter with a Beta kernel.

            Args:
                y (np.ndarray): Data array
                fs (int): Sample rate (Hz)
                duration (float, optional): Kernel duration (s). If None, reads from table.
                alpha (float, optional): Alpha shape parameter. If None, reads from table.
                beta (float, optional): Beta shape parameter. If None, reads from table.
                axis (int, optional): Axis to apply filter. Defaults to 0.
                normalize (bool, optional): Whether to normalize the filtered array by the kernel amplitude. Defaults to False.

            Returns:
                y_filt (np.ndarray): Filtered data array.
            """

            if any(filter(None, (duration, alpha, beta))):

                assert len(self) == 1, 'Specify one filter'

                duration, alpha, beta = map(float, self.fetch1('duration', 'alpha', 'beta'))

            # convert parameters based on sample rate
            precision = int(np.ceil(np.log10(fs)))
            x = np.arange(0, duration, 1/fs).round(precision)

            # impulse response
            B = (math.gamma(alpha) * math.gamma(beta))/math.gamma(alpha+beta)
            fx = (x**(alpha-1) * (1-x)**(beta-1))/B

            # pad and filter input
            y_filt = Filter.pad_filter(y, fx, axis=axis, normalize=normalize)

            return y_filt
        

    class Boxcar(dj.Part):
        definition = """
        -> master
        ---
        duration = 0.1: decimal(18,9) unsigned # filter duration (s)
        """

        def filt(
            self, 
            y: np.ndarray, 
            fs: int, 
            duration: float=None, 
            axis: int=0, 
            normalize: bool=False
            ) -> np.ndarray:
            """Filter with a boxcar kernel.

            Args:
                y (np.ndarray): Data array
                fs (int): Sample rate (Hz)
                duration (float, optional): Kernel duration (s). If None, reads from table.
                axis (int, optional): Axis to apply filter. Defaults to 0.
                normalize (bool, optional): Whether to normalize the filtered array by the kernel amplitude. Defaults to False.

            Returns:
                y_filt (np.ndarray): Filtered data array.
            """

            if duration is None:

                assert len(self) == 1, 'Specify one filter'

                duration = float(self.fetch1('duration'))

            # convert parameters based on sample rate
            wid = 1 + int(round(fs * duration))

            # impulse response
            fx = np.concatenate((
                np.zeros(int(np.floor(wid/2))), 
                np.ones(wid), 
                np.zeros(int(np.ceil(wid/2)))
            ))

            # pad and filter input
            y_filt = Filter.pad_filter(y, fx, axis=axis, normalize=normalize)

            return y_filt
    

    class Butterworth(dj.Part):
        definition = """
        -> master
        ---
        order = 2:       tinyint unsigned  # filter order
        low_cut = 500:   smallint unsigned # low-cut frequency (Hz)
        high_cut = null: smallint unsigned # high-cut frequency (Hz)
        """

        def filt(
            self, 
            y: np.ndarray, 
            fs: int, 
            order: int=None,
            low_cut: int=None,
            high_cut: int=None,
            axis: int=0, 
            normalize: bool=False
            ) -> np.ndarray:
            """Filter with a Butterworth filter.

            Args:
                y (np.ndarray): Data array
                fs (int): Sample rate (Hz)
                order (int, optional): Filter order. If None, reads from table.
                low_cut (int, optional): Low cut frequency (Hz). If None and high_cut or order is None, reads from table.
                high_cut (int, optional): High cut frequency (Hz). If None and low_cut or order is None, reads from table.
                axis (int, optional): Axis to apply filter. Defaults to 0.
                normalize (bool, optional): Whether to normalize the filtered array by the kernel amplitude. Defaults to False.

            Returns:
                y_filt (np.ndarray): Filtered data array.
            """

            if order is None and any(filter(None, (low_cut, high_cut))):

                assert len(self) == 1, 'Specify one filter'

                order, low_cut, high_cut = self.fetch1('order', 'low_cut', 'high_cut')
            
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
            sos = signal.butter(order, Wn, btype, fs=fs, output='sos')

            # filter input
            y_filt = signal.sosfiltfilt(sos, y, axis=axis)

            return y_filt
        

    class Gaussian(dj.Part):
        definition = """
        # Gaussian kernel
        -> master
        ---
        sd = 25e-3: decimal(18,9) unsigned # filter standard deviation (s)
        width = 4:  tinyint unsigned       # filter width (multiples of sd)
        """

        def filt(
            self, 
            y: np.ndarray, 
            fs: int, 
            sd: float=None,
            width: int=None,
            axis: int=0, 
            normalize: bool=False
            ) -> np.ndarray:
            """Filter with a Gaussian kernel.

            Args:
                y (np.ndarray): Data array
                fs (int): Sample rate (Hz)
                sd (float, optional): Kernel standard deviation (s). If None, reads from table.
                width (int, optional): Kernel width (multiples of sd). If None, reads from table.
                axis (int, optional): Axis to apply filter. Defaults to 0.
                normalize (bool, optional): Whether to normalize the filtered array by the kernel amplitude. Defaults to False.

            Returns:
                y_filt (np.ndarray): Filtered data array.
            """

            if sd is None and width is None:

                assert len(self) == 1, 'Specify one filter'

                sd = float(self.fetch1('sd'))
                width = self.fetch1('width')

            # convert parameters based on sample rate
            sd = fs * sd
            wid = round(sd * width)

            # impulse response
            x = np.arange(-wid,wid)
            fx = 1/(sd*np.sqrt(2*np.pi)) * np.exp(-x**2/(2*sd**2))

            # pad and filter input
            y_filt = Filter.pad_filter(y, fx, axis=axis, normalize=normalize)

            return y_filt

    @classmethod
    def pad_filter(self, y, fx, axis=0, normalize=False):

        # pad data array to length of impulse
        pad_len = [2 * (int(len(fx)/2), ) if idx==axis else (0,0) for idx in range(y.ndim)]

        y_pad = np.pad(y, pad_len, 'reflect')

        # reshape impulse response to match data array shape along filter dimension
        fx = fx.reshape(tuple(len(fx) if idx==axis else 1 for idx in range(y.ndim)))

        # filter input
        y_filt = signal.fftconvolve(y_pad, fx, mode='same', axes=axis)

        # truncate filtered signal to original length
        y_filt = y_filt[
            tuple([np.s_[pad[0]:-pad[1]] if idx==axis else np.s_[::] for idx, pad in enumerate(pad_len)])
        ]

        # normalize by magnitude of impule response
        if normalize:
            y_filt /= y_filt.max()

        return y_filt


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

        def plot(self, row_attr: str='ephys_channel_idx', column_attr: str='motor_unit_id'):

            for session_key in (dj.U('session_date') & self).fetch('KEY'):

                row_keys = (dj.U(row_attr) & (self & session_key)).fetch('KEY')
                column_keys = (dj.U(column_attr) & (self & session_key)).fetch('KEY')

                n_rows = len(row_keys)
                n_columns = len(column_keys)

                fig, axs = plt.subplots(n_rows, n_columns, figsize=(12,8), sharey='row')

                for idx, (row_key, col_key) \
                    in zip(np.ndindex((n_rows, n_columns)), itertools.product(row_keys, column_keys)):

                    template = (self & session_key & row_key & col_key).fetch1('motor_unit_template')

                    axs[idx].plot(template, 'k');

                    [axs[idx].spines[edge].set_visible(False) for edge in ['top','right']];

                    if idx[0] < n_rows-1:
                        axs[idx].spines['bottom'].set_visible(False)
                        axs[idx].set_xticks([])

                    if idx[1] > 0: 
                        axs[idx].spines['left'].set_visible(False)
                        axs[idx].set_yticks([])

                fig.tight_layout(rect=[0, 0.03, 1, 0.95])
                fig.suptitle('Session {}'.format(session_key['session_date']));

    def make(self, key):

        # get path to sort files
        emg_sort = EmgSort & key
        emg_sort_path = emg_sort.fetch1('emg_sort_path')

        # ensure local path
        emg_sort_path = reference.EngramTier.ensure_local(emg_sort_path)

        # load sort data
        if emg_sort & {'software': 'Myosort'}:

            if 'matlab_export' in emg_sort_path:

                # read data (and convert channels to 0-indexing)
                spikes = sio.loadmat(emg_sort_path + 'spikes.mat')['spikes'].flatten()
                labels = sio.loadmat(emg_sort_path + 'labels.mat')['labels'].flatten()
                channels = sio.loadmat(emg_sort_path + 'channels.mat')['channels'].flatten() - 1
                templates = sio.loadmat(emg_sort_path + 'templates.mat')['templates']

                # label group
                label_group = np.unique(labels)

            else:
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

                templates = None

        else:
            print('Spike sorter {} unrecognized. Unspecified import method.'.format(emg_sort.fetch1('software')))
            return None

        # construct motor unit keys
        motor_unit_keys = [
            dict(**key, motor_unit_id=idx, motor_unit_spike_indices=spikes[labels == group])
            for idx, group in enumerate(label_group)
        ]

        # insert motor units
        self.insert(motor_unit_keys)

        # construct template keys
        if np.any(templates):

            template_keys = []
            for chan_idx, unit_idx in itertools.product(range(templates.shape[0]), range(templates.shape[2])):

                template_keys.append({
                    **key, 
                    'motor_unit_id': unit_idx, 
                    **(acquisition.EmgChannelGroup.Channel & key & {'emg_channel_idx': channels[chan_idx]}).fetch1('KEY'),
                    'motor_unit_template': templates[chan_idx, :, unit_idx]
                })

            # insert motor unit templates
            self.Template.insert(template_keys)


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

        def plot(self, x_pad: float=1, y_pad: float=1):

            assert len(Neuron & self) == 1, 'Specify one neuron'

            neuron_key = (Neuron & self).fetch1('KEY')
            
            # electrode array model electrodes table
            array_electrodes = equipment.ElectrodeArrayModel.Electrode & (acquisition.BrainChannelGroup & neuron_key)

            # number of rows and columns on the array
            unique_electrode_x = dj.U('electrode_x').aggr(array_electrodes, count='count(*)')
            n_columns = len(unique_electrode_x)
            n_rows = np.array(unique_electrode_x.fetch('count')).max()

            # origin coordinate
            origin = np.vstack((array_electrodes).fetch('electrode_x', 'electrode_y')).min(axis=1)

            # x and y scales
            x_scale = (np.diff(sorted(unique_electrode_x.fetch('electrode_x'))).min() if n_columns > 1 else 1)

            min_dy_per_column = np.array([
                np.diff(sorted((array_electrodes & elec_x).fetch('electrode_y'))).min() 
                for elec_x in unique_electrode_x.fetch('KEY')
            ])
            y_scale = (min_dy_per_column.min() if n_rows > 1 else 1)

            # center and re-scale array electrode coordinates
            array_electrodes_scaled = array_electrodes.proj(
                electrode_x_norm='(electrode_x-{})/{}'.format(origin[0], x_scale / Decimal(str(x_pad))),
                electrode_y_norm='(electrode_y-{})/{}'.format(origin[1], y_scale / Decimal(str(y_pad)))
            )

            # electrode array configuration for the recorded neuron
            electrode_config = equipment.ElectrodeArrayConfig.Electrode & (acquisition.BrainChannelGroup & neuron_key)

            # neuron templates and scaled x-y coordinates
            neuron_templates, x_coords, y_coords = (self * electrode_config * array_electrodes_scaled)\
                .fetch('neuron_template', 'electrode_x_norm', 'electrode_y_norm')

            # mean center templates
            neuron_templates = np.stack(neuron_templates)
            neuron_templates -= neuron_templates.mean(axis=1, keepdims=True)

            # scaled template time vector
            t = np.linspace(-0.5, 0.5, neuron_templates.shape[1])

            # absolute maximum template value
            template_max = abs(neuron_templates).max()

            # plot
            plt.figure(figsize=(2*n_columns, n_rows/2))

            for x_coord, y_coord, template in zip(x_coords.astype(float), y_coords.astype(float), neuron_templates):

                plt.plot(t + x_coord, (template/template_max) + y_coord, 'k');



    def make(self, key):

        # get path to sort files
        brain_sort = BrainSort & key
        brain_sort_path = brain_sort.fetch1('brain_sort_path')

        # ensure local path
        brain_sort_path = reference.EngramTier.ensure_local(brain_sort_path)

        # load sort data
        if brain_sort & {'software': 'Kilosort'}:
            
            t_spike = np.load(brain_sort_path + 'spike_times.npy').astype(int)
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
        neuron_keys = [
            dict(**key, neuron_id=idx, neuron_isolation=group, neuron_spike_indices=t_spike[cluster_id == clus])
            for idx, (clus, group) in enumerate(zip(cluster_group['cluster_id'], cluster_group['group']))
        ]

        # load ephys file
        reader = (acquisition.EphysRecording.File & key).load()

        n_samples = reader.get_signal_size(block_index=0, seg_index=0)

        # fetch ephys channel keys and indices
        channel_keys = (acquisition.BrainChannelGroup.Channel & key).fetch('KEY')
        channel_indices = [chan_key['ephys_channel_idx'] for chan_key in channel_keys]

        # waveform duration (s)
        WAVEFORM_DUR = 2e-3

        # waveform length
        fs = (acquisition.EphysRecording & key).fetch1('ephys_recording_sample_rate')
        half_wave_len = int(round((fs * WAVEFORM_DUR) / 2))

        # construct template keys
        template_keys = []
        for neuron_key in neuron_keys:

            # read raw waveforms
            raw_waveforms = [
                reader.get_analogsignal_chunk(
                    block_index=0, 
                    seg_index=0, 
                    i_start=int(t_spk - half_wave_len),
                    i_stop=int(t_spk + half_wave_len),
                    channel_indexes=channel_indices
                )
            for t_spk in neuron_key['neuron_spike_indices']
            if t_spk >= half_wave_len and t_spk < n_samples-half_wave_len
            ]

            # rescale waveforms
            waveforms = np.array([
                reader.rescale_signal_raw_to_float(raw_waveform, dtype='float64', channel_indexes=channel_indices)
                for raw_waveform in raw_waveforms
            ])

            # average waveforms across spikes to get templates
            templates = waveforms.mean(axis=0).T

            # aggregate templates into keys
            template_keys.extend([
                dict(key, neuron_id=neuron_key['neuron_id'], **chan_key, neuron_template=template) 
                for chan_key, template in zip(channel_keys, templates)
            ])

        # insert neurons
        self.insert(neuron_keys)

        # insert templates
        self.Template.insert(template_keys)