import datajoint as dj
import numpy as np
from churchland_pipeline_python import lab, acquisition, processing, equipment
from churchland_pipeline_python.utilities import datasync
from . import pacman_acquisition
from brpylib import NsxFile, brpylib_ver
from datetime import datetime

schema = dj.schema('churchland_analyses_pacman_processing')

@schema
class AlignmentParams(dj.Manual):
    definition = """
    # Task state IDs used to align trials
    -> pacman_acquisition.Behavior
    alignment_params_id: tinyint unsigned
    ---
    -> pacman_acquisition.TaskState
    alignment_max_lag = 0.2: decimal(4,3) # maximum allowable lag (s)
    """
    
    @classmethod
    def populate(self, session_rel=acquisition.Session, task_state='InTarget', max_lag=0.2):

        # get key for task state
        task_state_key = (pacman_acquisition.TaskState & {'task_state_name':task_state}).fetch1('KEY')

        # insert task state for every session
        for behavior_key in (pacman_acquisition.Behavior & session_rel).fetch('KEY'):

            # alignment parameters
            align_params = dict(**behavior_key, **task_state_key, alignment_max_lag=max_lag)

            # skip if parameters in table
            if not self & align_params:

                if not self & behavior_key:

                    # set params ID to 0 if no entries for the session
                    align_params.update(alignment_params_id=0)
                else:
                    # set params ID to next unfilled index for the session
                    all_params_id = (self & behavior_key).fetch('alignment_params_id')
                    new_params_id = next(i for i in range(2+max(all_params_id)) if i not in all_params_id)
                    align_params.update(alignment_params_id=new_params_id)

                self.insert1(align_params)

@schema
class EphysTrialStart(dj.Imported):
    definition = """
    # Synchronizes continuous acquisition ephys data with behavior trials
    -> pacman_acquisition.Behavior.Trial
    ---
    ephys_trial_start = null: int unsigned # sample index (ephys time base) corresponding to the trial start
    """

    key_source = pacman_acquisition.Behavior.Trial & (acquisition.Session & processing.SyncBlock)

    def make(self, key):

        session_key = (acquisition.Session & key).fetch1('KEY')

        # ephys sample rate
        fs_ephys = (acquisition.EphysRecording & session_key).fetch1('ephys_sample_rate') 

        # all trial keys with simulation time
        trial_keys = (pacman_acquisition.Behavior.Trial & session_key).fetch('KEY','simulation_time',as_dict=True)

        # pop simulation time (Speedgoat clock) from trial key
        trial_time = [trial.pop('simulation_time',None) for trial in trial_keys]

        # sync block start index and encoded time stamp
        sync_block_start, sync_block_time = (processing.SyncBlock & session_key).fetch('sync_block_start', 'sync_block_time')

        # get trial start index in ephys time base
        ephys_trial_start_idx = datasync.ephystrialstart(fs_ephys, trial_time, sync_block_start, sync_block_time)

        # legacy adjustment
        if session_key['session_date'] <= datetime.strptime('2018-10-11','%Y-%m-%d').date():
            ephys_trial_start_idx += round(0.1 * fs_ephys)

        # append ephys trial start to key
        trial_keys = [dict(**trial, ephys_trial_start=i0) for trial,i0 in zip(trial_keys,ephys_trial_start_idx)]

        self.insert(trial_keys)


@schema
class SpikeFilter(dj.Lookup):
    definition = """
    # Set of filter parameters for smoothing spike trains
    -> processing.Filter
    """

# -------------------------------------------------------------------------------------------------------------------------------
# LEVEL 2
# -------------------------------------------------------------------------------------------------------------------------------

@schema
class MotorUnitPsth(dj.Computed):
    definition = """
    # Peri-stimulus time histogram
    -> processing.MotorUnit
    -> pacman_acquisition.Behavior.Condition
    -> pacman_acquisition.SessionBlock
    ---
    motor_unit_psth: longblob # psth
    -> SpikeFilter
    """

@schema
class NeuronPsth(dj.Computed):
    definition = """
    # Peri-stimulus time histogram
    -> processing.Neuron
    -> pacman_acquisition.Behavior.Condition
    -> pacman_acquisition.SessionBlock
    ---
    neuron_psth: longblob # psth
    -> SpikeFilter
    """

@schema
class TrialAlignment(dj.Computed):
    definition = """
    # Trial alignment indices for behavior and ephys data 
    -> EphysTrialStart
    -> AlignmentParams
    ---
    behavior_alignment: longblob # alignment indices for Speedgoat data
    ephys_alignment: longblob # alignment indices for Ephys data
    """
    
    # restrict to trials with a defined start index
    key_source = ((EphysTrialStart & 'ephys_trial_start') & (pacman_acquisition.Behavior.Trial & 'successful_trial')) \
        * AlignmentParams

    def make(self, key):

        # trial table
        trial_rel = pacman_acquisition.Behavior.Trial & key

        # fetch all parameters from key source
        full_key = (self.key_source & key).fetch1()

        # load cell parameters
        load_cell_rel = (acquisition.Session.Hardware & key & {'hardware':'5lb Load Cell'}) * equipment.Hardware.Parameter
        load_cell_capacity = (load_cell_rel & {'parameter':'force capacity'}).fetch1('parameter_value')
        load_cell_output = (load_cell_rel & {'parameter':'voltage output'}).fetch1('parameter_value')

        # convert load cell capacity from Volts to Newtons
        load_cell_capacity *= 4.44822

        # 25 ms Gaussian filter
        gauss_filt = processing.Filter.Gaussian & {'sd':25e-3, 'width':4}

        # set alignment index
        if pacman_acquisition.ConditionParams.Stim & trial_rel:

            # align to stimulation
            stim = trial_rel.fetch1('stim')
            align_idx = next(i for i in range(len(stim)) if stim[i])

        else:
            # align to task state
            task_state = trial_rel.fetch1('task_state')
            align_idx = next(i for i in range(len(task_state)) if task_state[i] == full_key['task_state_id'])

        # behavioral sample rate
        fs_beh = (acquisition.BehaviorRecording & key).fetch1('behavior_sample_rate')

        # fetch target force and time
        t, target_force = (pacman_acquisition.Behavior.Condition & trial_rel).fetch1('condition_time', 'condition_force')
        zero_idx = next(i for i in range(len(t)) if t[i]>=0)

        # phase correct dynamic conditions
        if not pacman_acquisition.ConditionParams.Static & trial_rel:

            # generate lag range
            max_lag = float(full_key['alignment_max_lag'])
            max_lag_samp = int(round(fs_beh * max_lag))
            lags = range(-max_lag_samp, 1+max_lag_samp)

            # truncate time indices  
            precision = int(np.log10(fs_beh))
            trunc_idx = np.nonzero((t>=round(t[0]+max_lag, precision)) & (t<=round(t[-1]-max_lag, precision)))[0]
            target_force = target_force[trunc_idx]
            align_idx_trunc = trunc_idx - zero_idx

            # fetch force data
            force_raw_online = trial_rel.fetch1('force_raw_online')
            force_max, force_offset = (pacman_acquisition.ConditionParams.Force & trial_rel).fetch1('force_max','force_offset')

            # function to convert force from Volts to Newtons
            convertforce = lambda frc: force_max * (frc/load_cell_output * load_cell_capacity/force_max - float(force_offset))

            # compute normalized mean squared error for each lag
            nmse = -np.inf*np.ones(1+2*max_lag_samp)
            for idx, lag in enumerate(lags):
                if (align_idx+lag+align_idx_trunc[-1]) < len(force_raw_online):
                    force_filt = gauss_filt.filter(convertforce(force_raw_online[align_idx+lag+align_idx_trunc]), fs_beh)
                    nmse[idx] = 1 - np.sqrt(np.mean((force_filt-target_force)**2)/np.var(target_force))

            # shift alignment indices by optimal lag
            align_idx += lags[np.argmax(nmse)]

        # behavior alignment indices
        behavior_alignment = np.array(range(len(t))) + align_idx - zero_idx
        key.update(behavior_alignment=behavior_alignment)

        # ephys alignment indices
        fs_ephys = (acquisition.EphysRecording & key).fetch1('ephys_sample_rate')
        ephys_alignment = np.round(fs_ephys * np.arange(t[0], t[-1]+1/fs_beh, 1/fs_ephys)) + (align_idx - zero_idx) * int(fs_ephys/fs_beh)
        ephys_alignment += (EphysTrialStart & key).fetch1('ephys_trial_start')
        ephys_alignment = ephys_alignment.astype(int)
        key.update(ephys_alignment=ephys_alignment)

        self.insert1(key)

# -------------------------------------------------------------------------------------------------------------------------------
# LEVEL 3
# -------------------------------------------------------------------------------------------------------------------------------    
@schema
class Emg(dj.Imported):
    definition = """
    # raw, trialized, and aligned EMG data
    -> acquisition.EmgChannelGroup
    -> TrialAlignment
    emg_channel: tinyint unsigned # channel number (indexed relative to EMG channel group)
    ---
    emg_voltage_signal: longblob # channel data
    """

@schema
class Force(dj.Computed):
    definition = """
    # Single trial force
    -> TrialAlignment
    ---
    force_raw = null: longblob # aligned raw (online) force [Volts]
    force_filt = null: longblob # offline filtered, aligned, and calibrated force [Newtons]
    """

@schema
class MotorUnitSpikes(dj.Computed):
    definition = """
    # Aligned motor unit trial spikes
    -> processing.MotorUnit
    -> TrialAlignment
    ---
    motor_unit_spikes: longblob # trial-aligned spike raster (logical)
    """

@schema
class NeuronSpikes(dj.Computed):
    definition = """
    # Aligned neuron trial spikes
    -> processing.Neuron
    -> TrialAlignment
    ---
    neuron_spikes: longblob # trial-aligned spike raster (logical)
    """

# -------------------------------------------------------------------------------------------------------------------------------
# LEVEL 4
# -------------------------------------------------------------------------------------------------------------------------------
    
@schema 
class BehaviorQuality(dj.Computed):
    definition = """
    # Behavior quality metrics
    -> Force
    ---
    max_err_target: decimal(6,4) # maximum (over time) absolute error, normalized by the range of the target force
    max_err_mean: decimal(6,4) # maximum (over time) absolute z-scored error
    mah_dist_target: decimal(6,4) # Mahalanobis distance relative to the target force
    mah_dist_mean: decimal(6,4) # Mahalanobis distance relative to the trial average
    """

@schema
class MotorUnitRate(dj.Computed):
    definition = """
    # Aligned motor unit trial firing rate
    -> MotorUnitSpikes
    ---
    motor_unit_rate: longblob # trial-aligned firing rate [Hz]
    -> SpikeFilter
    """
    
@schema
class NeuronRate(dj.Computed):
    definition = """
    # Aligned neuron trial firing rate
    -> NeuronSpikes
    ---
    neuron_rate: longblob # trial-aligned firing rate [Hz]
    -> SpikeFilter
    """

# -------------------------------------------------------------------------------------------------------------------------------
# LEVEL 5
# ------------------------------------------------------------------------------------------------------------------------------- 

@schema 
class GoodTrial(dj.Computed):
    definition = """
    # Trials that meet behavior quality thresholds
    -> BehaviorQuality
    ---
    """