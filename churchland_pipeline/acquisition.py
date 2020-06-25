import datajoint as dj
import os, sys
import re
from itertools import compress
from . import lab, ephys, reference
from pathlib import Path
sys.path.insert(0, str(Path(os.getcwd()).parents[0]) + '/brPY/')
from brpylib import NsxFile, brpylib_ver

schema = dj.schema('churchland_acquisition')

# -------------------------------------------------------------------------------------------------------------------------------
# LEVEL 0
# -------------------------------------------------------------------------------------------------------------------------------

@schema
class EngramPath(dj.Lookup):
    definition = """
    # Provides the local path to Engram whether working on the server or a local machine
    engram_tier : varchar(32)               # engram data tier name
    """

    contents = [
        ['locker'],
        ['labshare']
    ]

    def getlocalpath(self):

        assert len(self)==1, 'Request one path'

        path_parts = ['']
        engram_tier = self.fetch1('engram_tier')

        # check if we're on the U19 server
        if os.path.isdir('/srv'):
            path_parts.extend(['srv', engram_tier, 'churchland'])

        else:
            local_os = sys.platform
            local_os = local_os[:(min(3, len(local_os)))]
            if local_os.lower() == 'lin':
                path_parts.append('mnt')

            elif local_os.lower() == 'win':
                path_parts.append('Y:') # will this always be true?

            elif local_os.lower() == 'dar':
                path_parts.append('Volumes')

            path_parts.extend(['Churchland-' + engram_tier, ''])

        return os.path.sep.join(path_parts)

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
        
        def printnotes(session, notesId=0):
            """
            Fetch and print notes
            """
            
            print((Session.Notes & {'session_date': session, 'session_notes_id': notesId}).fetch1('session_notes'))
            
            
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

        local_path = (EngramPath & {'engram_tier': 'locker'}).getlocalpath()
        raw_path_parts = [rig, task.lower()+'-task', monkey.lower(), 'raw', '']
        return local_path + os.path.sep.join(raw_path_parts)
    
    @classmethod
    def populate(self, monkey, rig, task):
        """
        Auto-populate session data
        """
        
        # check keys
        assert len(lab.Monkey & {'monkey': monkey})==1, 'Unrecognized monkey'
        assert len(lab.Rig & {'rig': rig})==1,          'Unrecognized rig'
        assert len(Task & {'task': task})==1,           'Unrecognized task'

        # session dates
        raw_path = Session.getrawpath(monkey, rig, task)
        dates = sorted(list(os.listdir(raw_path)))
        dates = [x for x in dates if re.search('\d{4}-\d{2}-\d{2}',x) is not None]

        # import session data (can make task-specific later)
        for date in dates:
            
            sessFiles = os.listdir(raw_path + date + '/')
            
            # this will need to be updated for non-blackrock data files
            if (not any(Session & {'session_date': date})
                and all([x in os.listdir(raw_path + date + '/') for x in ['speedgoat','blackrock']])):

                    # insert session
                    Session.insert1((date,monkey,rig,task))

                    # insert users
                    Session.User.insert1((date,monkey,'njm2149'))
                    if date >= '2019-11-01':
                        Session.User.insert1((date,monkey,'emt2177'))

                    # insert notes
                    notesIdx = [re.search('.*notes\.txt',x) for x in sessFiles]
                    if any(notesIdx):

                        notesFile = sessFiles[list(compress(range(len(notesIdx)), notesIdx))[0]]
                        fid = open(raw_path + date + '/' + notesFile,'r')
                        notes = fid.read()
                        fid.close()

                        Session.Notes.insert1((date,monkey,0,notes))
        

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
    ephys_channel_count : smallint unsigned # number of channels on the recording file
    """

    class BlackrockParams(dj.Part):
        definition = """
        # Ephys params unique to Blackrock system
        -> master
        ---
        blackrock_timestamp : double # number of samples between pressing "record" and the clock start
        """
    
    @property
    def key_source(self):
        return Session & {'session_date': '2019-12-16'}
    
    def make(self, key):
        
        # fetch session key
        sess_key = (Session & key).fetch(as_dict=True)[0]

        # raw data path
        raw_path = Session.getrawpath(sess_key['monkey'],sess_key['rig'],sess_key['task']) + str(sess_key['session_date']) + '/'

        # find ephys file
        if 'blackrock' in os.listdir(raw_path):

            eph_path = raw_path + 'blackrock/'
            prog = re.compile('.*(emg|neu|neu_emg)_00\d\.ns\d')
            nsx_path = [eph_path + file for file in os.listdir(eph_path) if prog.search(file) is not None]

            for i, pth in enumerate(nsx_path):

                key['ephys_file_id'] = i
                primary_key = key.copy()
                
                key['ephys_file_path'] = pth

                # read channel count from basic header 
                nsx_file = NsxFile(pth)
                key['ephys_channel_count'] = nsx_file.basic_header['ChannelCount']

                # read additional parameters from data file
                nsxData = nsx_file.getdata(nsx_file.extended_headers[0]['ElectrodeID'])
                key['ephys_sample_rate'] = int(nsxData['samp_per_s'])
                key['ephys_duration'] = nsxData['data_time_s']

                # insert self
                self.insert1(key)

                # append Timestamp and save to Blackrock part table
                key = primary_key.copy()
                key['blackrock_timestamp'] = nsxData['data_headers'][0]['Timestamp']
                self.BlackrockParams.insert1(key)

                # close NSx file
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
        
        # fetch session key
        sess_key = (Session & key).fetch(as_dict=True)[0]
        
        # raw data path
        raw_path = Session.getrawpath(sess_key['monkey'],sess_key['rig'],sess_key['task'])
        
        # find summary file
        sg_path = raw_path + str(key['session_date']) + '/speedgoat/'
        sg_files = list(os.listdir(sg_path))
        prog = re.compile('.*\.summary')
        summary_file = [x for x in sg_files if prog.search(x) is not None][0]
        
        # save summary file path to key
        key['behavior_summary_file_path'] = sg_path + summary_file
        key['behavior_sample_rate'] = int(1e3)
        
        # insert key
        self.insert1(key)

# -------------------------------------------------------------------------------------------------------------------------------
# LEVEL 3
# -------------------------------------------------------------------------------------------------------------------------------

@schema
class EmgChannelGroup(dj.Imported):
    definition = """
    -> EphysRecording
    -> reference.Muscle
    ---
    -> ephys.EmgElectrode
    emg_channel_group : blob # array of channel ID numbers corresponding to EMG data
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
    neural_channel_group : blob # array of channel ID numbers corresponding to neural data
    neural_channel_notes : varchar(4095) # notes for the channel set
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
    sync_channel : smallint unsigned # sync channel ID number
    """
    
    def make(self, key):
        
        # fetch file path
        file_path = (EphysRecording & key).fetch1('ephys_file_path')
        
        # identify file type
        if re.search('\.ns\d$',file_path):
            
            # read NSx file
            nsx_file = NsxFile(file_path)
            
            # identify sync electrode ID
            key['sync_channel'] = ([header['ElectrodeID'] for header in nsx_file.extended_headers
                                           if header['ElectrodeLabel']=='ainp16'][0])
            
            # close file
            nsx_file.close()
            
        else:
            print('Unrecognized file type')
            return
        
        # insert key
        self.insert1(key)