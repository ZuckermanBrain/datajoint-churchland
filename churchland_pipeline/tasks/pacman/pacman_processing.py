import datajoint as dj
from ... import lab, acquisition, processing
from . import pacman_acquisition

schema = dj.schema('churchland_shared_pacman_processing')

@schema
class AlignmentState(dj.Lookup):
    definition = """
    # Task state IDs used to align trials
    -> pacman_acquisition.TaskState
    ---
    """
    
    contents = [
        [5]
    ]

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
    motor_unit_psth : longblob # psth
    -> processing.Filter
    """

@schema
class NeuronPsth(dj.Computed):
    definition = """
    # Peri-stimulus time histogram
    -> processing.Neuron
    -> pacman_acquisition.Behavior.Condition
    -> pacman_acquisition.SessionBlock
    ---
    neuron_psth : longblob # psth
    -> processing.Filter
    """

@schema
class TrialAlignment(dj.Imported):
    definition = """
    # Alignment indices for each behavior trial
    -> AlignmentState
    -> pacman_acquisition.Behavior.Trial
    ---
    -> acquisition.EphysRecording.Channel
    alignment_index : int unsigned # alignment index (in Speedgoat time base)
    speedgoat_alignment : longblob # alignment indices for Speedgoat data
    ephys_alignment : longblob # alignment indices for Ephys data
    """

# -------------------------------------------------------------------------------------------------------------------------------
# LEVEL 3
# -------------------------------------------------------------------------------------------------------------------------------    
@schema
class Emg(dj.Imported):
    definition = """
    # raw, trialized, and aligned EMG data
    -> acquisition.EmgChannelGroup
    -> TrialAlignment
    emg_channel : tinyint unsigned # channel number (indexed relative to EMG channel group)
    ---
    emg_voltage_signal : longblob # channel data
    """

@schema
class Force(dj.Computed):
    definition = """
    # Single trial force
    -> TrialAlignment
    ---
    force_raw = null : longblob # aligned raw (online) force [Volts]
    force_filt = null : longblob # offline filtered, aligned, and calibrated force [Newtons]
    """

@schema
class MotorUnitSpikes(dj.Computed):
    definition = """
    # Aligned motor unit trial spikes
    -> processing.MotorUnit
    -> TrialAlignment
    ---
    motor_unit_spikes : longblob # trial-aligned spike raster (logical)
    """

@schema
class NeuronSpikes(dj.Computed):
    definition = """
    # Aligned neuron trial spikes
    -> processing.Neuron
    -> TrialAlignment
    ---
    neuron_spikes : longblob # trial-aligned spike raster (logical)
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
    max_err_target : decimal(6,4) # maximum (over time) absolute error, normalized by the range of the target force
    max_err_mean : decimal(6,4) # maximum (over time) absolute z-scored error
    mah_dist_target : decimal(6,4) # Mahalanobis distance relative to the target force
    mah_dist_mean : decimal(6,4) # Mahalanobis distance relative to the trial average
    """

@schema
class MotorUnitRate(dj.Computed):
    definition = """
    # Aligned motor unit trial firing rate
    -> MotorUnitSpikes
    ---
    motor_unit_rate : longblob # trial-aligned firing rate [Hz]
    -> processing.Filter
    """
    
@schema
class NeuronRate(dj.Computed):
    definition = """
    # Aligned neuron trial firing rate
    -> NeuronSpikes
    ---
    neuron_rate : longblob # trial-aligned firing rate [Hz]
    -> processing.Filter
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