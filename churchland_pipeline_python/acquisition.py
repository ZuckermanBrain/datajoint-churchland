import datajoint as dj
import os, re
import neo
from . import lab, equipment, reference, action
from typing import List, Tuple

schema = dj.schema('churchland_common_acquisition') 

# =======
# LEVEL 0
# =======

@schema
class Task(dj.Lookup):
    definition = """
    # Experimental tasks
    task:         varchar(32) # task name
    task_version: varchar(8)  # task version
    ---
    -> equipment.Hardware.proj(task_controller_hardware = 'hardware')
    -> equipment.Software.proj(task_controller_software = 'software', task_controller_software_version = 'software_version')
    -> equipment.Software.proj(graphics = 'software', graphics_version = 'software_version')
    task_description = '': varchar(255) # additional task details
    """
    
    contents = [
        #task name    |version |controller hardware |controller software |version |graphics       |version |task description
        ['pacman',     '1.0',   'Speedgoat',         'Simulink',          '',      'Psychtoolbox', '3.0',   '1-dimensional force tracking'],
        ['two target', '1.0',   'Speedgoat',         'Simulink',          '',      'Unity 3D',     '',      ''],
        ['reaching',   '1.0',   'Speedgoat',         'Simulink',          '',      'Psychtoolbox', '3.0',   ''],
    ]


# =======
# LEVEL 1
# =======

@schema
class Session(dj.Manual):
    definition = """
    # Recording session
    session_date:                     date         # session date
    -> lab.Monkey
    ---
    -> lab.Rig
    -> Task
    session_problem = 0:              bool         # session problem. If True, session is excluded from analyses
    session_problem_description = '': varchar(255) # session problem description (e.g., corrupted data)
    """

    class Hardware(dj.Part):
        definition = """
        # Hardware used for the recording session
        -> master
        -> equipment.Hardware
        """

    class User(dj.Part):
        definition = """
        # Session personnel
        -> master
        -> lab.User
        """

    class Notes(dj.Part):
        definition = """
        # Session notes
        -> master
        session_notes_id:   tinyint unsigned # session notes ID number
        ---
        session_notes = '': varchar(4095)    # session notes text
        """
        
        def printnotes(self):
            """Fetch and print notes."""
            
            for key in self:
                print((self & key).fetch1('session_notes'))
        
    @classmethod
    def getrawpath(self, monkey: str, rig: str, task: str) -> str:
        """Get path to raw data."""

        # get local path to locker
        local_path = (reference.EngramTier & {'engram_tier': 'locker'}).getlocalpath()

        # get local path to raw data (rig > task > monkey)
        raw_path_parts = [rig, task.lower()+'-task', monkey.lower(), 'raw']
        
        return local_path + os.path.sep.join(raw_path_parts)

    @classmethod
    def populate(self,
        monkey: str,
        rig: str,
        task: Tuple[str, str],
        dates: List[str]=None,
        neural_signal_processor: str='Cerebus'
    ) -> None:
        """Auto populates raw session data, assuming that the data files are stored on
        the Engram locker under (rig > task > monkey)

        Args:
            monkey: monkey name
            rig: rig name
            task: task name, version
            dates: list of dates to restrict import
            neural_signal_processor: neural signal processor name
        """

        # check inputs and map to primary keys of appropriate tables
        input_key = {}
        input_table = {monkey: lab.Monkey, rig: lab.Rig, task: Task, neural_signal_processor: equipment.Hardware}
        for input, table in input_table.items():

            key = {k:v for k,v in zip(table.primary_key, ([input] if isinstance(input,str) else input))}

            assert len(table & key), 'Unrecognized input {}. Limit table {} to one entry'.format(input, table.table_name)

            input_key.update({input: (table & key).fetch1('KEY')})

        # input values as table primary keys
        monkey_key = input_key[monkey]
        rig_key    = input_key[rig]
        task_key   = input_key[task]
        nsp_key    = input_key[neural_signal_processor]

        # find all directories in raw path
        raw_path = self.getrawpath(monkey_key['monkey'], rig_key['rig'], task_key['task'])
        raw_dir = sorted(list(os.listdir(raw_path)))

        if dates:
            # restrict dates based on user list
            session_dates = [d for d in raw_dir if d in dates]
        else:
            # get all dates from directory list
            session_dates = [d for d in raw_dir if re.search(r'\d{4}-\d{2}-\d{2}',d) is not None]

        # filter session dates by those not in table
        session_dates = [date for date in session_dates if not self & {'session_date': date}]

        for date in session_dates:

            session_path = os.path.sep.join([raw_path, date, ''])
            session_files = os.listdir(session_path)

            # ensure behavior directory exists
            try:
                if (Task & task_key).fetch1('task_controller_hardware') == 'Speedgoat':
                    behavior_dir = 'speedgoat'

                next(filter(lambda x: x==behavior_dir, session_files))

            except StopIteration:
                print('Missing behavior files for session {}'.format(date))

            else:         
                # ensure ephys directory exists
                try:
                    if nsp_key['hardware'] == 'Cerebus': # will add IMEC for new probes
                        ephys_dir = 'blackrock'

                    next(filter(lambda x: x==ephys_dir, session_files))

                except StopIteration:
                    print('Missing ephys files for session {}'.format(date))
                    
                else:
                    # session key
                    session_key = dict(session_date=date, **monkey_key)
                    
                    # insert session
                    self.insert1(dict(**session_key, **rig_key, **task_key))

                    # insert notes
                    try:
                        notes_files = next(x for x in session_files if re.search('.*notes\.txt',x))
                    except StopIteration:
                        print('Missing notes for session {}'.format(date))
                    else:
                        with open(session_path + notes_files,'r') as f:
                            self.Notes.insert1(dict(**session_key, session_notes_id=0, session_notes=f.read()))

                    # insert neural signal processor
                    self.Hardware.insert1(dict(**session_key, **nsp_key))


# =======
# LEVEL 2
# =======

@schema
class BehaviorRecording(dj.Imported):
    definition = """
    # Behavior recording
    -> Session
    ---
    behavior_summary_file_path: varchar(1012)     # behavior summary file path
    behavior_sample_rate = 1e3: smallint unsigned # behavior sample rate (Hz)
    """

    # remove problem sessions from key source
    key_source = Session - 'session_problem'
    
    def make(self, key):
        
        session_key = (Session & key).fetch1()
        
        # path to raw data
        raw_path = os.path.sep.join([
            Session.getrawpath(session_key['monkey'],session_key['rig'],session_key['task']),
            str(session_key['session_date'])
        ])
        
        # identify task controller
        task_controller_hardware = (Task & Session & session_key).fetch1('task_controller_hardware')

        if task_controller_hardware == 'Speedgoat':

            # path to speedgoat files
            speedgoat_path = os.path.sep.join([raw_path, 'speedgoat', ''])
            speedgoat_files = list(os.listdir(speedgoat_path))

            # speedgoat summary file
            summary_file = next(f for f in speedgoat_files if re.search('.*\.summary',f))

            # ensure file path is "global" (i.e., relative to U19 server)
            key['behavior_summary_file_path'] = (reference.EngramTier & {'engram_tier':'locker'}).ensureremote(speedgoat_path + summary_file)

        # behavior sample rate
        key['behavior_sample_rate'] = int(1e3)
        
        # insert key
        self.insert1(key)


@schema
class EphysRecording(dj.Imported):
    definition = """
    # Electrophysiological recording
    -> Session
    ephys_file_id:     tinyint unsigned  # ephys file ID number
    ---
    ephys_file_path:   varchar(1012)     # ephys file path
    ephys_sample_rate: smallint unsigned # ephys sample rate (Hz)
    ephys_duration:    double            # ephys recording duration (s)
    """

    class Channel(dj.Part):
        definition = """
        # Ephys channel header
        -> master
        channel_idx:       smallint unsigned                    # channel index in data array
        ---
        channel_id = null: smallint unsigned                    # channel ID number used by Blackrock system
        channel_type:      enum('brain', 'emg', 'sync', 'stim') # channel data type
        """
    
    key_source = Session - 'session_problem'

    def make(self, key):
        
        session_key = (Session & key).fetch1()

        # path to raw data
        raw_path = os.path.sep.join([
            Session.getrawpath(session_key['monkey'],session_key['rig'],session_key['task']),
            str(session_key['session_date'])
        ])

        # fetch neural signal processor
        session_hardware = (Session.Hardware & session_key) * equipment.Hardware
        neural_signal_processor = (session_hardware & {'equipment_category': 'neural signal processor'}).fetch1('hardware')

        if neural_signal_processor == 'Cerebus':

            # path to blackrock files
            blackrock_path = os.path.sep.join([raw_path, 'blackrock', ''])
            blackrock_files = list(os.listdir(blackrock_path))

            # path to NSx files
            nsx_files = [f for f in blackrock_files \
                if re.search(r'.*(emg|neu|neu_emg)_00\d\.ns\d',f) is not None and 'settling' not in f]
            nsx_path = [blackrock_path + f for f in nsx_files]

            for i, pth in enumerate(nsx_path):

                key['ephys_file_id'] = i
                primary_key = key.copy()

                # read NSx file
                reader = neo.rawio.BlackrockRawIO(pth)
                reader.parse_header()

                # pull sample rate and recording duration
                key['ephys_sample_rate'] = int(next(iter(reader.sig_sampling_rates.values())))
                key['ephys_duration'] = reader.get_signal_size(0,0) / key['ephys_sample_rate']

                # ensure file path is "global" (i.e., relative to U19 server)
                key['ephys_file_path'] = (reference.EngramTier & {'engram_tier':'locker'}).ensureremote(pth)

                # insert self
                self.insert1(key)

                # channel header name and ID indices
                name_idx, id_idx = [
                    idx for idx, name in enumerate(reader.header['signal_channels'].dtype.names) \
                    if name in ['name','id']
                ]

                # insert channel header information //TODO double check the map files use the ID and not the label
                for j, chan in enumerate(reader.header['signal_channels']):

                    key = primary_key.copy()
                    key['channel_idx'] = j
                    key['channel_id'] = chan[id_idx]
                    chan_name = chan[name_idx]

                    if re.search('^\d', chan_name):
                        key['channel_type'] = 'brain'

                    elif re.search('ainp[1-8]$', chan_name):
                        key['channel_type'] = 'emg'

                    elif chan_name == 'ainp15':
                        key['channel_type'] = 'stim'

                    elif chan_name == 'ainp16':
                        key['channel_type'] = 'sync'

                    self.Channel.insert1(key)


@schema
class EphysStimulation(dj.Manual):
    definition = """
    # Electrophysiological stimulation
    -> Session
    ephys_stimulation_probe_id: tinyint unsigned  # ephys stimulation probe ID number
    ---
    -> equipment.ElectrodeArray
    probe_depth = null:         decimal(5,3)      # depth of neural probe tip relative to cortical surface (mm)
    """


# =======
# LEVEL 3
# =======

@schema
class BrainChannelGroup(dj.Manual):
    definition = """
    -> EphysRecording
    -> reference.BrainRegion
    brain_channel_group_id:         tinyint unsigned      # brain channel group ID number
    ---
    -> equipment.ElectrodeArray
    -> [nullable] action.BurrHole
    brain_hemisphere:               enum('left', 'right') # brain hemisphere
    brain_channel_group_notes = '': varchar(4095)         # brain channel group notes
    probe_depth = null:             decimal(5,3)          # depth of neural probe tip relative to cortical surface (mm)
    -> [nullable] equipment.ElectrodeArrayConfig
    """

    class Channel(dj.Part):
        definition = """
        # Channel number in recording file
        -> master
        -> EphysRecording.Channel
        ---
        brain_channel_idx: smallint unsigned # brain channel index
        """


@schema
class EmgChannelGroup(dj.Manual):
    definition = """
    -> EphysRecording
    -> reference.Muscle
    emg_channel_group_id:         tinyint unsigned # emg channel group ID number
    ---
    -> equipment.ElectrodeArray
    emg_channel_group_notes = '': varchar(4095)    # emg channel group notes
    -> [nullable] equipment.ElectrodeArrayConfig
    """

    class Channel(dj.Part):
        definition = """
        # Channel number in recording file
        -> master
        -> EphysRecording.Channel
        ---
        emg_channel_idx:     smallint unsigned                      # EMG channel index
        emg_channel_quality: enum('sortable', 'unsortable', 'dead') # EMG channel quality
        """
