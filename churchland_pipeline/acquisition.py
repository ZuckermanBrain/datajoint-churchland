import os, sys, pathlib
sys.path.insert(0, str(pathlib.Path(os.getcwd()).parents[0]) + '/brPY/')
import datajoint as dj
import re
from . import lab, equipment, reference
from brpylib import NsxFile, brpylib_ver
from collections import ChainMap

schema = dj.schema('churchland_common_acquisition')

# -------------------------------------------------------------------------------------------------------------------------------
# LEVEL 0
# -------------------------------------------------------------------------------------------------------------------------------

@schema
class SaveTagType(dj.Lookup):
    definition = """
    # Save tag types
    save_tag_type : varchar(32) # unique save tag type
    ---
    save_tag_description : varchar(255)
    """

    contents = [
        ['setup', 'getting setup'],
        ['good',  'clear for analysis'],
        ['bad behavior', 'inconsistent behavior unsuitable for analyses'],
        ['unstable neurons', 'neural drift']
    ]

@schema
class Task(dj.Lookup):
    definition = """
    # Experimental tasks
    task : varchar(32) # unique task name
    ---
    task_description : varchar(255) # additional task details
    """
    
    contents = [
        ['pacman', ''],
        ['pedaling', ''],
        ['reaching', '']
    ]

# -------------------------------------------------------------------------------------------------------------------------------
# LEVEL 1
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

    class Equipment(dj.Part):
        definition = """
        # Equipment used for the recording session
        -> master
        -> equipment.Equipment
        """

    class User(dj.Part):
        definition = """
        -> master
        -> lab.User
        ---
        """

    class Notes(dj.Part):
        definition = """
        # Session note
        -> master
        session_notes_id : tinyint unsigned # note ID
        ---
        session_notes: varchar(4095) # note text
        """
        
        def printnotes(self, session, notesId=0):
            """
            Fetch and print notes
            """
            
            print((self & {'session_date': session, 'session_notes_id': notesId}).fetch1('session_notes'))
            
            
    class SaveTag(dj.Part):
        definition = """
        # Save tags and associated notes
        -> master
        save_tag: tinyint unsigned # save tag
        ---
        -> SaveTagType
        save_tag_notes: varchar(4095) # notes for the save tag
        """
        
    class Problem(dj.Part):
        definition = """
        # Problem with specified session
        -> master
        ---
        problem_cause: varchar(255) # (e.g. corrupted data)
        """
        
    @classmethod
    def getrawpath(self, monkey, rig, task):
        """
        Get path to raw data
        """

        local_path = (reference.EngramPath & {'engram_tier': 'locker'}).getlocalpath()
        raw_path_parts = [rig, task.lower()+'-task', monkey.lower(), 'raw', '']
        return local_path + os.path.sep.join(raw_path_parts)

    @classmethod
    def populate(self,
        monkey, 
        rig, 
        task, 
        dates=[],
        neural_signal_processor='Cerebus',
        task_controller_hardware='Speedgoat', 
        task_controller_software='Simulink'):

        # session dates
        raw_path = self.getrawpath(monkey, rig, task)
        sess_dates = sorted(list(os.listdir(raw_path)))

        if len(dates) > 0:
            dates = list(filter(lambda x: x in dates, sess_dates))
        else:
            dates = list(filter(lambda x: re.search(r'\d{4}-\d{2}-\d{2}',x), sess_dates))

        for date in dates:

            sess_path = raw_path + date + '/'
            sess_files = os.listdir(sess_path)

            # ensure session data not already in database
            if not self & {'session_date': date}:

                # ensure behavior directory exists
                try:
                    if task_controller_hardware == 'Speedgoat':
                        behavior_dir = 'speedgoat'

                    next(filter(lambda x: x==behavior_dir, sess_files))
                except StopIteration:
                    print('Missing behavior files for session {}'.format(date))
                else:         

                    # ensure ephys directory exists
                    try:
                        if neural_signal_processor == 'Cerebus': # will add IMEC for new probes
                            ephys_dir = 'blackrock'

                        next(filter(lambda x: x==ephys_dir, sess_files))
                    except StopIteration:
                        print('Missing ephys files for session {}'.format(date))
                    else:

                        # insert session
                        self.insert1((date, monkey, rig, task))

                        # insert notes
                        try:
                            notes_files = next(x for x in sess_files if re.search('.*notes\.txt',x))
                        except StopIteration:
                            print('Missing notes for session {}'.format(date))
                        else:
                            with open(sess_path + notes_files,'r') as f:
                                self.Notes.insert1((date, monkey, 0, f.read()))

                        # insert common equipment
                        common_equipment = [neural_signal_processor, task_controller_hardware, task_controller_software]
                        equip_name = list(map(lambda equip: {'equipment_name': equip}, common_equipment))
                        equip_keys = [(equipment.Equipment & attr).fetch1('KEY') for attr in equip_name]
                        equip_keys = [dict(ChainMap({'session_date': date, 'monkey': monkey}, d)) for d in equip_keys]
                        self.Equipment.insert(equip_keys)

# -------------------------------------------------------------------------------------------------------------------------------
# LEVEL 2
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
    """

    class BlackrockParams(dj.Part):
        definition = """
        # Ephys params unique to Blackrock system
        -> master
        ---
        blackrock_timestamp : double # number of samples between pressing "record" and the clock start
        """

    class Channel(dj.Part):
        definition = """
        # Ephys channel header
        -> master
        channel_index : smallint unsigned # channel index in data array
        ---
        channel_id = null : smallint unsigned # channel ID used by Blackrock system
        channel_label : enum('neural', 'emg', 'sync', 'stim')
        """
    
    def make(self, key):
        
        # fetch session key
        sess_key = (Session & key).fetch1()

        # raw data path
        raw_path = Session.getrawpath(sess_key['monkey'],sess_key['rig'],sess_key['task']) + str(sess_key['session_date'])

        # identify task controller
        sess_equip = (Session.Equipment & sess_key) * equipment.Equipment
        neural_signal_processor = (sess_equip & {'equipment_type': 'neural signal processor'}).fetch1('equipment_name')

        if neural_signal_processor == 'Cerebus':

            # path to blackrock files
            eph_path = raw_path + '/blackrock/'
            eph_files = list(os.listdir(eph_path))

            # path to NSx files
            nsx_files = list(filter(lambda x: re.search(r'.*(emg|neu|neu_emg)_00\d\.ns\d',x), eph_files))
            nsx_path = [eph_path + f for f in nsx_files]

            for i, pth in enumerate(nsx_path):

                key['ephys_file_id'] = i
                primary_key = key.copy()

                # read NSx file
                nsx_file = NsxFile(pth)

                # read data from first channel
                nsx_data = nsx_file.getdata(nsx_file.extended_headers[0]['ElectrodeID'])

                # pull sample rate and recording duration
                key['ephys_sample_rate'] = int(nsx_data['samp_per_s'])
                key['ephys_duration'] = nsx_data['data_time_s']

                # ensure global file path before inserting
                key['ephys_file_path'] = (reference.EngramPath & {'engram_tier':'locker'}).ensureglobal(pth)

                # insert self
                self.insert1(key)

                # append Timestamp and save to Blackrock part table
                key = primary_key.copy()
                key['blackrock_timestamp'] = nsx_data['data_headers'][0]['Timestamp']
                self.BlackrockParams.insert1(key)

                # insert channel header information //TODO double check the map files use the ID and not the label
                for j, elec in enumerate(nsx_file.extended_headers):
                    key = primary_key.copy()
                    key['channel_index'] = j
                    key['channel_id'] = elec['ElectrodeID']
                    if re.search('^\d',elec['ElectrodeLabel']):
                        key['channel_label'] = 'neural'

                    elif re.search('ainp[1-8]$', elec['ElectrodeLabel']):
                        key['channel_label'] = 'emg'

                    elif elec['ElectrodeLabel'] == 'ainp15':
                        key['channel_label'] = 'stim'

                    elif elec['ElectrodeLabel'] == 'ainp16':
                        key['channel_label'] = 'sync'

                    self.Channel.insert1(key)

                # close file
                nsx_file.close()
                
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
        
        # session key
        sess_key = (Session & key).fetch1()
        
        # path to behavioral files
        raw_path = Session.getrawpath(sess_key['monkey'],sess_key['rig'],sess_key['task']) + str(key['session_date'])
        
        # identify task controller
        sess_equip = (Session.Equipment & sess_key) * equipment.Equipment
        task_controller_hardware = (sess_equip & {'equipment_type': 'task controller hardware'}).fetch1('equipment_name')

        if task_controller_hardware == 'Speedgoat':

            # path to speedgoat files
            beh_path = raw_path + '/speedgoat/'
            beh_files = list(os.listdir(beh_path))

            # get speedgoat summary file
            summary_file = next(filter(lambda x: re.search('.*\.summary',x), beh_files))

            # ensure global file path
            key['behavior_summary_file_path'] = (reference.EngramPath & {'engram_tier':'locker'}).ensureglobal(beh_path + summary_file)

        # behavior sample rate
        key['behavior_sample_rate'] = int(1e3)
        
        # insert key
        self.insert1(key)

# -------------------------------------------------------------------------------------------------------------------------------
# LEVEL 3
# -------------------------------------------------------------------------------------------------------------------------------

@schema
class EmgChannelGroup(dj.Manual):
    definition = """
    -> EphysRecording
    -> reference.Muscle
    ---
    emg_channel_notes : varchar(4095) # notes for the channel set
    """

    class Channel(dj.Part):
        definition = """
        # EMG channel number in group
        -> master
        -> EphysRecording.Channel
        emg_channel : smallint unsigned # EMG channel index in group
        ---
        emg_channel_quality : enum('sortable', 'hash', 'dead') # EMG channel quality
        """


@schema
class NeuralChannelGroup(dj.Manual):
    definition = """
    -> EphysRecording
    -> reference.BrainRegion
    neural_electrode_id: tinyint unsigned # recording electrode number
    ---
    hemisphere : enum('left', 'right') # which hemisphere are we recording from
    neural_channel_notes : varchar(4095) # notes for the channel set
    """

    class Channel(dj.Part):
        definition = """
        # Channel number in group
        -> master
        -> EphysRecording.Channel
        neural_channel : smallint unsigned # neural channel index in group
        """

    class ProbeDepth(dj.Part):
        definition = """
        # Depth of recording probe relative to cortical surface
        -> master
        -> Session.SaveTag
        ---
        probe_depth : decimal(5,3) # depth of recording electrode [mm]
        """