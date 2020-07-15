import datajoint as dj
from ... import lab, acquisition, equipment, reference
from ...rigs.Jumanji import speedgoat
import os, re
import numpy as np
from collections import ChainMap

schema = dj.schema('churchland_shared_pacman_acquisition')

# -------------------------------------------------------------------------------------------------------------------------------
# LEVEL 0
# -------------------------------------------------------------------------------------------------------------------------------

@schema 
class ArmPosture(dj.Lookup):
    definition = """
    # Arm posture
    -> lab.Monkey
    posture_id: tinyint unsigned # unique posture ID number
    ---
    elbow_angle: tinyint unsigned # elbow flexion angle in degrees (0 = fully flexed)
    shoulder_angle: tinyint unsigned # shoulder flexion angle in degrees (0 = arm by side)
    """
    
    contents = [
        ['Cousteau', 1, 90, 65],
        ['Cousteau', 2, 90, 40],
        ['Cousteau', 3, 90, 75]
    ]

@schema
class ConditionParams(dj.Lookup):
    definition = """
    # Task condition parameters
    condition_id: smallint unsigned
    """

    class Force(dj.Part):
        definition = """
        # Force parameters for Pac-Man task
        -> master
        force_id: smallint unsigned # ID number
        ---
        force_max: tinyint unsigned # maximum force (N)
        force_offset: decimal(5,4) # baseline force (N)
        force_inverted: bool # if false, then pushing on the load cell moves PacMan upwards onscreen
        """
        
    class Stim(dj.Part):
        definition = """
        # Cerestim parameters
        -> master
        stim_id: smallint unsigned # ID number
        ---
        stim_current: smallint unsigned # stim current (uA)
        stim_electrode: smallint unsigned # stim electrode number
        stim_delay: double # time relative to target onset when stim TTL was delivered (s)
        stim_polarity: tinyint unsigned # stim polarity
        stim_pulses: tinyint unsigned # number of pulses in stim train
        stim_width1: smallint unsigned # first pulse duration (us)
        stim_width2: smallint unsigned # second pulse duration (us)
        stim_interphase: smallint unsigned # interphase duration (us)
        stim_frequency: smallint unsigned # stim frequency (Hz)
        """

    class Target(dj.Part):
        definition = """
        # Target force profiles for Pac-Man task
        -> master
        target_id: smallint unsigned # ID number
        ---
        target_duration: decimal(5,4) # target duration (s)
        target_offset: decimal(5,4) # offset from baseline [proportion playable window]
        target_pad: decimal(5,4) # duration of "padding" dots leading into and out of target (s)
        """
        
    class Static(dj.Part):
        definition = """
        # Static force profile (type code: STA)
        -> ConditionParams.Target
        ---
        """
        
    class Ramp(dj.Part):
        definition = """
        # Linear ramp force profile (type code: RMP)
        -> ConditionParams.Target
        ---
        target_amplitude: decimal(5,4) # target amplitude [proportion playable window]
        """
        
    class Sine(dj.Part):
        definition = """
        # Sinusoidal (single-frequency) force profile (type code: SIN)
        -> ConditionParams.Target
        ---
        target_amplitude: decimal(5,4) # target amplitude [proportion playable window]
        target_frequency: decimal(5,4) # sinusoid frequency [Hz]
        """
        
    class Chirp(dj.Part):
        definition = """
        # Chirp force profile (type code: CHP)
        -> ConditionParams.Target
        ---
        target_amplitude: decimal(5,4) # target amplitude [proportion playable window]
        target_frequency_init: decimal(5,4) # initial frequency [Hz]
        target_frequency_final: decimal(5,4) # final frequency [Hz]
        """
        
    @classmethod
    def params2keys(self, params):
        """
        Converts a parameters dictionary into a set of condition keys and a derived
        condition table.

        Args:
            params (dict): trial parameters saved by Speedgoat
        """

        # force key
        force_key = {
            'force_max': params['frcMax'], 
            'force_offset': params['frcOff'],
            'force_inverted': params['frcPol']==-1
            }

        cond_rel = ConditionParams.Force

        # stim key
        if 'stim' in params.keys() and params['stim']==1:
                
            prog = re.compile('stim([A-Z]\w*)')
            stim_key = dict(ChainMap(*[
                {'stim_' + prog.search(k).group(1).lower(): v} 
                for k,v in zip(params.keys(), params.values()) 
                if prog.search(k) is not None
                ]))

            cond_rel = cond_rel * ConditionParams.Stim
            
        else:
            stim_key = dict()

        # target key
        targ_key = {
            'target_duration': params['duration'],
            'target_offset': params['offset'][0],
            'target_pad': params['padDur']
        }

        if params['type'] == 'STA':

            targ_rel = ConditionParams.Static
            targ_type_key = dict()

        elif params['type'] == 'RMP':

            targ_rel = ConditionParams.Ramp
            targ_type_key = {'target_amplitude': params['amplitude'][0]}

        elif params['type'] == 'SIN':

            targ_rel = ConditionParams.Sine
            targ_type_key = {
                'target_amplitude': params['amplitude'][0],
                'target_frequency': params['frequency'][0]
            }

        elif params['type'] == 'CHP':

            targ_rel = ConditionParams.Chirp
            targ_type_key = {
                'target_amplitude': params['amplitude'][0],
                'target_frequency_init': params['frequency'][0],
                'target_frequency_final': params['frequency'][1]
            }

        cond_rel = cond_rel * ConditionParams.Target * targ_rel

        return force_key, stim_key, targ_key, targ_type_key, cond_rel, targ_rel


    
@schema
class TaskState(dj.Lookup):
    definition = """
    # Simulink Stateflow task state IDs and names
    task_state_id: tinyint unsigned # task state ID number
    ---
    task_state_name: varchar(255) # unique task state name
    """
    
    contents = [
        [0,   'Init'],
        [1,   'Delay'],
        [2,   'PreTrial'],
        [3,   'FirstDotAppears'],
        [4,   'InFirstPad'],
        [5,   'InTarget'],
        [6,   'InSecondPad'],
        [7,   'PastLastDot'],
        [100, 'Success'],
        [251, 'Glitch'],
        [252, 'Abort'],
        [253, 'Failure'] 
    ]
    
# -------------------------------------------------------------------------------------------------------------------------------
# LEVEL 1
# -------------------------------------------------------------------------------------------------------------------------------
    
@schema
class Behavior(dj.Imported):
    definition = """
    # Behavioral data imported from Speedgoat
    -> acquisition.BehaviorRecording
    ---
    """
    
    class Condition(dj.Part):
        definition = """
        # Condition data
        -> master
        -> ConditionParams
        """

    class Trial(dj.Part):
        definition = """
        # Trial data
        -> master
        trial_number: smallint unsigned # trial number (within session)
        ---
        -> Behavior.Condition
        save_tag: tinyint unsigned # save tag
        successful_trial: bool
        simulation_time: longblob # absolute simulation time
        task_state: longblob # task state IDs
        force_raw_online: longblob # amplified output of load cell
        force_filt_online: longblob # online (boxcar) filtered and normalized force used to control Pac-Man
        reward: longblob # TTL signal indicating the delivery of juice reward
        photobox: longblob # photobox signal
        stim = null: longblob # TTL signal indicating the delivery of a stim pulse
        """

    key_source = (acquisition.BehaviorRecording & {'session_date':'2018-10-02'})
        
    def make(self, key):

        # insert entry to Behavior table
        Behavior.insert1(key)

        # local path to behavioral summary file and sample rate
        beh_sum_path, fs = (acquisition.BehaviorRecording & key).fetch1('behavior_summary_file_path', 'behavior_sample_rate')
        beh_sum_path = (reference.EngramPath & {'engram_tier': 'locker'}).ensurelocal(beh_sum_path)

        # path to all behavior files
        beh_path = os.path.sep.join(beh_sum_path.split(os.path.sep)[:-1] + [''])

        # identify task controller
        sess_equip = (acquisition.Session.Equipment & key) * equipment.Equipment
        task_controller_hardware = (sess_equip & {'equipment_type': 'task controller hardware'}).fetch1('equipment_name')

        if task_controller_hardware == 'Speedgoat':

            # load summary file
            summary = speedgoat.readtaskstates(beh_sum_path)

            # update task states
            TaskState.insert(summary, skip_duplicates=True)

            # parameter and data files
            beh_files = os.listdir(beh_path)
            param_files = list(filter(lambda f: f.endswith('.params'), beh_files))
            data_files = list(filter(lambda f: f.endswith('.data'), beh_files))

            # populate conditions from parameter files
            for f_param in param_files:

                # trial number
                trial = re.search(r'beh_(\d*)',f_param).group(1)

                # ensure matching data file exists
                if f_param.replace('params','data') in data_files:
                    
                    # read params file
                    params = speedgoat.readtrialparams(beh_path + f_param)

                    # convert params to condition keys
                    force_key, stim_key, targ_key, targ_type_key, cond_rel, targ_rel = ConditionParams.params2keys(params)
                    
                    # insert new condition if none exists
                    if not(cond_rel & force_key & stim_key & targ_key):

                        # insert condition table
                        if not(ConditionParams()):
                            new_cond_id = 0
                        else:
                            cond_id = ConditionParams.fetch('condition_id')
                            new_cond_id = np.setdiff1d(np.arange(cond_id.max()+2), cond_id)[0]

                        cond_key = {'condition_id': new_cond_id}
                        ConditionParams.insert1(cond_key)

                        # insert first-layer condition part tables
                        for (p,k) in zip(['Force', 'Stim', 'Target'], [force_key, stim_key, targ_key]):

                            if not(k):
                                continue

                            part = getattr(ConditionParams, p)
                            k_id = p.lower() + '_id'

                            if not(part & k):

                                if not(part()):
                                    new_id = 0
                                else:
                                    id = part.fetch(k_id)
                                    new_id = np.setdiff1d(np.arange(id.max()+2), id)[0]

                                k[k_id] = new_id
                            else:
                                k[k_id] = np.unique((part & k).fetch(k_id))[0]

                            part.insert1(dict(ChainMap(cond_key, k)))

                        # insert second-layer condition target type part table
                        if not(targ_rel & {'target_id': targ_key['target_id']} & targ_type_key):
                            
                            targ_rel.insert1(dict(ChainMap(cond_key, {'target_id': targ_key['target_id']}, targ_type_key)))

                else:
                    print('Missing data file for trial {}'.format(trial))

            # populate trials from data files
            success_state = (TaskState() & 'task_state_name="Success"').fetch1('task_state_id')

            for f_data in data_files:

                # trial number
                trial = int(re.search(r'beh_(\d*)',f_data).group(1))

                # find matching parameters file
                try:
                    param_file = next(filter(lambda f: f_data.replace('data','params')==f, param_files))
                except StopIteration:
                    print('Missing parameters file for trial {}'.format(trial))
                else:
                    # convert params to condition keys
                    params = speedgoat.readtrialparams(beh_path + param_file)
                    force_key, stim_key, targ_key, targ_type_key, cond_rel, targ_rel = ConditionParams.params2keys(params)

                    # read data
                    data = speedgoat.readtrialdata(beh_path + f_data, success_state, fs)

                    # insert condition data
                    cond_id = (cond_rel & force_key & stim_key & targ_key).fetch1('condition_id')
                    cond_key = dict(ChainMap(key, {'condition_id': cond_id}))
                    Behavior.Condition.insert1(cond_key, skip_duplicates=True)

                    # insert trial data
                    trial_key = dict(ChainMap(cond_key, {'trial_number': trial}, {'save_tag': params['saveTag']}, data))
                    Behavior.Trial.insert1(trial_key)


@schema
class SessionBlock(dj.Manual):
    definition = """
    # Set of save tags and arm postures for conducting analyses
    -> acquisition.Session
    block_id: tinyint unsigned # block ID
    ---
    -> ArmPosture
    """
    
    class SaveTag(dj.Part):
        definition = """
        # Block save tags
        -> master
        -> acquisition.Session.SaveTag
        """