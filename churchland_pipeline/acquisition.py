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
    -> lab.Rig
    """

    class User(dj.Part):
        definition = """
        -> master
        -> lab.User
        ---
        """

    class Notes(dj.Part):
        definition = """
        # Session notes
        -> master
        ---
        session_notes: varchar(4095)
        """

    class SaveTag(dj.Part):
        definition = """
        # Save tags and associated notes
        -> master
        save_tag: tinyint unsigned # save tag
        ---
        save_tag_notes: varchar(4095) # notes for the save tag
        """
        
    class Problem(dj.Part):
        definition = """
        # Problem with specified session
        -> master
        ---
        problem_cause: varchar(255) # (e.g. corrupted data)
        """

# -------------------------------------------------------------------------------------------------------------------------------
# LEVEL 1
# -------------------------------------------------------------------------------------------------------------------------------

@schema
class EphysRecording(dj.Imported):
    definition = """
    -> Session
    ---
    ephys_file_path: varchar(1012) # file path (temporary until issues with filepath attribute are resolved)
    """

    class AcquisitionParams(dj.Part):
        definition = """
        # Acquisition parameters for Ephys recording (inferred from Blackrock file)
        -> master
        ---
        ephys_sample_rate : smallint unsigned # sample rate [Hz]
        ephys_time_stamp : double # number of samples between pressing "record" and the clock start (Blackrock parameter)
        ephys_data_samples : int unsigned # recording duration [samples]
        ephys_data_duration : double # recording duration [sec]
        ephys_channel_count : smallint unsigned # number of channels on the recording file
        """

@schema
class SpeedgoatRecording(dj.Imported):
    definition = """
    -> Session
    ---
    speedgoat_file_path: varchar(1012) # file path (temporary until issues with filepath attribute are resolved)
    """

    class AcquisitionParams(dj.Part):
        definition = """
        # Acquisition parameters for Speedgoat recording
        -> master
        ---
        speedgoat_sample_rate = 1e3 : smallint unsigned # sample rate [Hz]
        """

# -------------------------------------------------------------------------------------------------------------------------------
# LEVEL 2
# -------------------------------------------------------------------------------------------------------------------------------

@schema
class EmgChannelGroup(dj.Imported):
    definition = """
    -> EphysRecording
    -> reference.Muscle
    ---
    -> ephys.EmgElectrode
    emg_channel_group : blob # array of channel numbers corresponding to EMG data
    emg_channel_notes : varchar(4095) # notes for the channel set
    """

    class Sortable(dj.Part):
        definition = """
        # Subset of EMG channels ammenable to spike sorting
        -> master
        ---
        sortable_emg_channels : blob # subset of channels used for spike sorting 
        """   

@schema
class NeuralChannelGroup(dj.Imported):
    definition = """
    -> EphysRecording
    -> reference.BrainRegion
    neural_electrode_id: tinyint unsigned # electrode number
    ---
    -> ephys.NeuralElectrode
    hemisphere : enum("left","right") # which hemisphere are we recording from
    neural_channel_group: blob # array of channel numbers corresponding to neural data
    neural_channel_notes: varchar(4095) # notes for the channel set
    """

    class ProbeDepth(dj.Part):
        definition = """
        # Depth of recording probe relative to cortical surface (N/A for array recordings)
        -> master
        -> Session.SaveTag
        ---
        probe_depth = null : decimal(5,3) # depth of recording electrode [mm]
        """     
        
@schema
class SyncChannel(dj.Imported):
    definition = """
    # Channel containing encoded signal for synchronizing ephys data with Speedgoat
    -> EphysRecording
    ---
    sync_channel_number: smallint unsigned # channel number
    """
