import datajoint as dj
from . import lab, ephys, reference

schema = dj.schema('churchland_acquisition')

# -------------------------------------------------------------------------------------------------------------------------------
# LEVEL 0
# -------------------------------------------------------------------------------------------------------------------------------

@schema
class Session(dj.Manual):
    definition = """
    # Recording session
    session_date: date # session date
    -> lab.Monkey
    ---
    -> lab.User
    -> [nullable] lab.User.proj(user2 = 'user') # secondary experimenter
    -> [nullable] lab.User.proj(user3 = 'user') # tertiary experimenter
    """
    
    class Notes(dj.Part):
        definition = """
        # Session notes
        -> master
        ---
        session_notes: varchar(8192)
        """
        
    class SaveTag(dj.Part):
        definition = """
        # Save tags and associated notes
        -> master
        ---
        save_tag: tinyint unsigned # save tag
        save_tag_notes: varchar(2048) # notes for the save tag
        """
        
# -------------------------------------------------------------------------------------------------------------------------------
# LEVEL 1
# ------------------------------------------------------------------------------------------------------------------------------- 

@schema
class EphysRecording(dj.Imported):
    definition = """
    -> Session
    ---
    ephys_file_path: varchar(512) # file path
    ephys_file_name: varchar(256) # file name
    """
    
    class Meta(dj.Part):
        definition = """
        # Meta parameters for Ephys recording
        -> master
        ---
        ephys_sample_rate : smallint unsigned # sample rate [Hz]
        ephys_time_stamp : double # clock start time [sec]
        ephys_data_samples : int unsigned # recording duration [samples]
        ephys_data_duration : double # recording duration [sec]
        ephys_channel_count : smallint unsigned # number of channels on the recording file
        """
    
@schema
class ProblematicSession(dj.Manual):
    definition = """
    # Problematic sessions
    -> Session
    ---
    problem_reason = '' : varchar(256)
    """
    
@schema
class SpeedgoatRecording(dj.Imported):
    definition = """
    -> Session
    ---
    speedgoat_file_path: varchar(512) # file path
    speedgoat_file_name: varchar(256) # file name
    """
    
    class Meta(dj.Part):
        definition = """
        # Meta parameters for Speedgoat recording
        -> master
        ---
        speedgoat_sample_rate : smallint unsigned # sample rate [Hz]
        """

# -------------------------------------------------------------------------------------------------------------------------------
# LEVEL 2
# ------------------------------------------------------------------------------------------------------------------------------- 
    
@schema
class EmgChannels(dj.Imported):
    definition = """
    -> EphysRecording
    -> reference.Muscle
    ---
    -> ephys.EmgElectrode
    emg_channel_group : blob # array of channel numbers corresponding to EMG data
    emg_channel_notes : varchar(1024) # notes for the channel set
    """   
    
@schema
class NeuralChannels(dj.Imported):
    definition = """
    -> EphysRecording
    -> reference.BrainRegion
    neural_electrode_id: tinyint unsigned # electrode number
    ---
    -> ephys.NeuralElectrode
    neural_channel_group: blob # array of channel numbers corresponding to neural data
    neural_channel_notes: varchar(1024) # notes for the channel set
    """
    
    class ProbeDepth(dj.Part):
        definition = """
        # Depth of recording probe relative to cortical surface
        -> master
        -> Session.SaveTag
        ---
        probe_depth : decimal(5,3) # depth of recording electrode [mm]
        """
    
@schema
class SyncChannel(dj.Imported):
    definition = """
    -> EphysRecording
    ---
    sync_channel_number: smallint unsigned # channel number
    time_stamp: double # clock start time
    data_duration: double # recording duration (seconds)
    """

# -------------------------------------------------------------------------------------------------------------------------------
# LEVEL 3
# ------------------------------------------------------------------------------------------------------------------------------- 
    
@schema 
class CorruptedEmgChannels(dj.Manual):
    definition = """
    # EMG channels to exclude from analyses
    -> EmgChannels
    ---
    corrupted_emg_channels = null : blob # array of corrupted channels
    """