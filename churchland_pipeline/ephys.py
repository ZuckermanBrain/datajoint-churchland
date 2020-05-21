import datajoint as dj

schema = dj.schema('churchland_ephys')

@schema
class EmgElectrode(dj.Lookup):
    definition = """
    emg_electrode_abbrev: varchar(20) # unique electrode abbreviation
    ---
    emg_electrode_manufacturer: varchar(50) # electrode manufacturer
    emg_electrode_name: varchar(100) # full electrode name
    emg_electrode_channel_count: smallint unsigned # total number of active recording channels on the electrode
    """

@schema
class NeuralElectrode(dj.Lookup):
    definition = """
    neural_electrode_abbrev: varchar(20) # unique electrode abbreviation
    ---
    neural_electrode_manufacturer: varchar(50) # electrode manufacturer
    neural_electrode_name: varchar(100) # full electrode name
    neural_electrode_type: enum("probe","mea") # electrode type (linear probe or microelectrode array)
    neural_electrode_channel_count: smallint unsigned # total number of active recording channels on the electrode
    """
    
# Neural Stimulator    