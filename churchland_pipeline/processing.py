import datajoint as dj
from . import acquisition

schema = dj.schema('churchland_processing')

# -------------------------------------------------------------------------------------------------------------------------------
# LEVEL 0
# -------------------------------------------------------------------------------------------------------------------------------

@schema
class EmgSpikeSorter(dj.Lookup):
    definition = """
    # Spike sorter for EMG data
    emg_sorter_name : varchar(255)
    emg_sorter_version : varchar(255)
    ---
    """
    
@schema    
class NeuralSpikeSorter(dj.Lookup):
    definition = """
    # Spike sorter for neural data
    neural_sorter_name : varchar(255)
    neural_sorter_version : varchar(255)
    ---
    """
    
    contents = [
        ['Kilosort','1'],
        ['Kilosort','2']
    ]

# -------------------------------------------------------------------------------------------------------------------------------
# LEVEL 1
# -------------------------------------------------------------------------------------------------------------------------------

@schema
class MotorUnit(dj.Imported):
    definition = """
    # Sorted motor unit
    -> acquisition.EmgChannelGroup
    motor_unit_id : smallint unsigned # unique unit ID
    ---
    -> EmgSpikeSorter
    """
    
    class SessionSpikes(dj.Part):
        definition = """
        # Full session spike indices
        -> master
        ---
        motor_unit_spike_indices : longblob # array of spike indices
        """
        
    class Template(dj.Part):
        definition = """
        # Sorted spike templates
        -> master
        emg_channel : smallint unsigned # EMG channel number
        ---
        motor_unit_template : longblob # waveform template
        """

@schema
class Neuron(dj.Imported):
    definition = """
    # Sorted neuron
    -> acquisition.NeuralChannelGroup
    neuron_id : smallint unsigned # unique unit ID
    ---
    -> NeuralSpikeSorter
    neuron_isolation : enum("single","multi") # neuron isolation quality (single- or multi-unit)
    """
    
    class SessionSpikes(dj.Part):
        definition = """
        # Full session spike indices
        -> master
        ---
        neuron_spike_indices : longblob # array of spike indices
        """
        
    class Template(dj.Part):
        definition = """
        # Sorted spike templates
        -> master
        neural_channel : smallint unsigned # neural channel number
        ---
        neuron_template : longblob # waveform template
        """