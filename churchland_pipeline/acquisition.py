import datajoint as dj
import os
import re
from . import lab, ephys, reference

schema = dj.schema('churchland_acquisition')

# -------------------------------------------------------------------------------------------------------------------------------
# LEVEL 0
# -------------------------------------------------------------------------------------------------------------------------------

@schema
class Task(dj.Lookup):
    definition = """
    # Experimental tasks
    task : varchar(32) # unique task name
    ---
    task_description : varchar(255) # additional task details
    """
    
    contents = [
        ['Pacman', ''],
        ['Pedaling', ''],
        ['Reaching', '']
    ]

# -------------------------------------------------------------------------------------------------------------------------------
# LEVEL ...
# -------------------------------------------------------------------------------------------------------------------------------

@schema
class Session(dj.Manual):
    definition = """
    # Recording session
    session_date: date # session date
    -> lab.Monkey
    ---
    -> lab.Rig
    -> Task
    """

    class User(dj.Part):
        definition = """
        -> master
        -> lab.User
        ---
        """

    class Note(dj.Part):
        definition = """
        # Session note
        -> master
        session_note_id : tinyint unsigned # note ID
        ---
        session_note: varchar(4095) # note text
        """

    class SaveTag(dj.Part):
        definition = """
        # Save tags and associated notes
        -> master
        save_tag: tinyint unsigned # save tag
        ---
        save_tag_note: varchar(4095) # notes for the save tag
        """
        
    class Problem(dj.Part):
        definition = """
        # Problem with specified session
        -> master
        ---
        problem_cause: varchar(255) # (e.g. corrupted data)
        """

# -------------------------------------------------------------------------------------------------------------------------------
# LEVEL ...
# -------------------------------------------------------------------------------------------------------------------------------

@schema
class EphysRecording(dj.Imported):
    definition = """
    # Electrophysiological recording
    -> Session
    ephys_file_id : tinyint unsigned # file ID
    ---
    ephys_file_path: varchar(1012) # file path (temporary until issues with filepath attribute are resolved)
    ephys_sample_rate : smallint unsigned # sampling rate for ephys data  [Hz]
    ephys_duration : double # recording duration [sec]
    ephys_channel_count : smallint unsigned # number of channels on the recording file
    """

    class BlackrockParams(dj.Part):
        definition = """
        # Ephys params unique to Blackrock system
        -> master
        ---
        blackrock_time_stamp : double # number of samples between pressing "record" and the clock start
        """

@schema
class BehaviorRecording(dj.Imported):
    definition = """
    # Behavior recording, imported from Speedgoat files
    -> Session
    ---
    behavior_summary_file_path : varchar(1012) # path to summary file (temporary)
    behavior_sample_rate = 1e3 : smallint unsigned # sampling rate for behavioral data [Hz]
    """
    
    def make(self, key):
        
        # fetch session key
        sessKey = (Session & key).fetch(as_dict=True)[0]
        
        # raw data path
        rawPath = ('/srv/locker/churchland/{}/{}-task/{}/raw/'
                   .format(sessKey['rig'], sessKey['task'].lower(), sessKey['monkey'].lower()))
        
        # find summary file
        sgPath = rawPath + str(key['session_date']) + '/speedgoat/'
        sgFiles = list(os.listdir(sgPath))
        prog = re.compile('.*\.summary')
        summaryFile = [x for x in sgFiles if prog.search(x) is not None][0]
        
        # save summary file path to key
        key['behavior_summary_file_path'] = sgPath + summaryFile
        key['behavior_sample_rate'] = int(1e3)
        
        # insert key
        self.insert(key)

# -------------------------------------------------------------------------------------------------------------------------------
# LEVEL ...
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
    # Channel containing encoded signal for synchronizing ephys data with behavior
    -> EphysRecording
    ---
    sync_channel_number: smallint unsigned # channel number
    """
