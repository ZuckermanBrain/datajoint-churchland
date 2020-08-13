import datajoint as dj
from . import acquisition, equipment

schema = dj.schema('churchland_common_processing')

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