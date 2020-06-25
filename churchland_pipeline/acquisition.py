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
class Path(dj.Lookup):
    definition = """
    global_path          : varchar(255)                 # global path name
    system               : enum('windows','mac','linux')
    ---
    local_path           : varchar(255)                 # local computer path
    net_location         : varchar(255)                 # location on the network
    description=''       : varchar(255)
    """

    contents = [
       ['/srv/locker/churchland', 'mac', '/Volumes/churchland-locker', '', '']
    ]

    def get_local_path(self, path, local_os=None):
        # determine local os
        if local_os is None:
            local_os = sys.platform
            local_os = local_os[:(min(3, len(local_os)))]
        if local_os.lower() == 'glo':
            local = 0
            home = '~'
        elif local_os.lower() == 'lin':
            local = 1
            home = os.environ['HOME']
        elif local_os.lower() == 'win':
            local = 2
            home = os.environ['HOME']
        elif local_os.lower() == 'dar':
            local = 3
            home = '~'
        else:
            raise NameError('unknown OS')
        path = path.replace(os.path.sep, '/')
        path = path.replace('~', home)
        globs = dj.U('global_path') & self
        systems = ['linux', 'windows', 'mac']
        mapping = [[], []]
        for iglob, glob in enumerate(globs.fetch('KEY')):
            mapping[iglob].append(glob['global_path'])
            for system in systems:
                mapping[iglob].append((self & glob & {'system': system}).fetch1('local_path'))
        mapping = np.asarray(mapping)
        for i in range(len(globs)):
            for j in range(len(systems)):
                n = len(mapping[i, j])
                if j != local and path[:n] == mapping[i, j][:n]:
                    path = os.path.join(mapping[i, local], path[n+1:])
                    break
        if os.path.sep == '\\' and local_os.lower() != 'glo':
            path = path.replace('/', '\\')
        else:
            path = path.replace('\\', '/')
        return path

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
        
    
    def quickinsert(monkey, rig, task):
        """
        Quickly insert session data
        """
        
        # check keys
        assert len(lab.Monkey & {'monkey': monkey})==1, 'Unrecognized monkey'
        assert len(lab.Rig & {'rig': rig})==1,          'Unrecognized rig'
        assert len(Task & {'task': task})==1,           'Unrecognized task'

        # session dates
        rawPath = Session.rawpath(rig,task,monkey)
        dates = sorted(list(os.listdir(rawPath)))
        dates = [x for x in dates if re.search('\d{4}-\d{2}-\d{2}',x) is not None]

        # import session data (can make task-specific later)
        for date in dates:
            
            sessFiles = os.listdir(rawPath + date + '/')
            
            # this will need to be updated for non-blackrock data files
            if (not any(Session & {'session_date': date})
                and all([x in os.listdir(rawPath + date + '/') for x in ['speedgoat','blackrock']])):

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
                        fid = open(rawPath + date + '/' + notesFile,'r')
                        notes = fid.read()
                        fid.close()

                        Session.Notes.insert1((date,monkey,0,notes))
                        
    def rawpath(rig,task,monkey):
        """
        Get path to raw data
        """
        
        return '/srv/locker/churchland/{}/{}-task/{}/raw/'.format(rig, task.lower(), monkey.lower())
        

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
        sessKey = (Session & key).fetch(as_dict=True)[0]

        # raw data path
        rawPath = Session.rawpath(sessKey['rig'],sessKey['task'],sessKey['monkey']) + str(sessKey['session_date']) + '/'

        # find ephys file
        if 'blackrock' in os.listdir(rawPath):

            ephPath = rawPath + 'blackrock/'
            prog = re.compile('.*(emg|neu|neu_emg)_00\d\.ns\d')
            nsxPath = [ephPath + file for file in os.listdir(ephPath) if prog.search(file) is not None]

            for i, pth in enumerate(nsxPath):

                key['ephys_file_id'] = i
                primaryKey = key.copy()
                
                key['ephys_file_path'] = pth

                # read channel count from basic header 
                nsxFile = NsxFile(pth)
                key['ephys_channel_count'] = nsxFile.basic_header['ChannelCount']

                # read additional parameters from data file
                nsxData = nsxFile.getdata(nsxFile.extended_headers[0]['ElectrodeID'])
                key['ephys_sample_rate'] = int(nsxData['samp_per_s'])
                key['ephys_duration'] = nsxData['data_time_s']

                # insert self
                self.insert1(key)

                # append Timestamp and save to Blackrock part table
                key = primaryKey.copy()
                key['blackrock_timestamp'] = nsxData['data_headers'][0]['Timestamp']
                self.BlackrockParams.insert1(key)

                # close NSx file
                nsxFile.close()
                
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
        rawPath = Session.rawpath(sessKey['rig'],sessKey['task'],sessKey['monkey'])
        
        # find summary file
        sgPath = rawPath + str(key['session_date']) + '/speedgoat/'
        sgFiles = list(os.listdir(sgPath))
        prog = re.compile('.*\.summary')
        summaryFile = [x for x in sgFiles if prog.search(x) is not None][0]
        
        # save summary file path to key
        key['behavior_summary_file_path'] = sgPath + summaryFile
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
        filePath = (EphysRecording & key).fetch1('ephys_file_path')
        
        # identify file type
        if re.search('\.ns\d$',filePath):
            
            # read NSx file
            nsxFile = NsxFile(filePath)
            
            # identify sync electrode ID
            key['sync_channel'] = ([header['ElectrodeID'] for header in nsxFile.extended_headers
                                           if header['ElectrodeLabel']=='ainp16'][0])
            
            # close file
            nsxFile.close()
            
        else:
            print('Unrecognized file type')
            return
        
        # insert key
        self.insert1(key)