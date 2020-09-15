import datajoint as dj
from churchland_pipeline_python import lab, acquisition, processing
from churchland_pipeline_python.utilities import datasync
from . import pacman_acquisition
from brpylib import NsxFile, brpylib_ver
from datetime import datetime

schema = dj.schema('churchland_analyses_pacman_processing')

@schema
class AlignmentState(dj.Lookup):
    definition = """
    # Task state IDs used to align trials
    -> pacman_acquisition.TaskState
    """

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
    -> AlignmentState
    ---
    behavior_alignment: longblob # alignment indices for Speedgoat data
    ephys_alignment: longblob # alignment indices for Ephys data
    """

    key_source = EphysTrialStart & 'successful_trial'

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