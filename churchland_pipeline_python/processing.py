import os, sys, pathlib
sys.path.insert(0, str(pathlib.Path(os.getcwd()).parents[0]))
sys.path.insert(0, str(pathlib.Path(os.getcwd()).parents[0]) + '/brPY/')
import datajoint as dj
from . import acquisition, equipment
from .utilities import datasync
from brpylib import NsxFile, brpylib_ver

schema = dj.schema('churchland_analyses_processing')

# -------------------------------------------------------------------------------------------------------------------------------
# LEVEL 0
# -------------------------------------------------------------------------------------------------------------------------------

@schema
class Filter(dj.Lookup):
    definition = """
    # Filter bank
    filter_name: varchar(16) # filter class (e.g. Butterworth)
    filter_id: smallint unsigned # unique filter identifier
    ---
    """
    
    class Beta(dj.Part):
        definition = """
        # Beta kernel
        -> master
        ---
        duration: decimal(5,3) # interval kernel is defined over [seconds]
        alpha: decimal(5,3) # shape parameter
        beta: decimal(5,3) # shape parameter
        """
        
    class Boxcar(dj.Part):
        definition = """
        -> master
        ---
        duration: decimal(5,3) # filter duration [seconds]
        """
    
    class Butterworth(dj.Part):
        definition = """
        -> master
        ---
        order: tinyint unsigned # filter order
        low_cut = null: smallint unsigned # low-cut frequency [Hz]
        high_cut = null: smallint unsigned # high-cut frequency [Hz]
        """
        
    class Gaussian(dj.Part):
        definition = """
        # Gaussian kernel
        -> master
        ---
        sd: decimal(7,6) # filter standard deviation [seconds]
        width: tinyint unsigned # filter width [multiples of standard deviations]
        """
        
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