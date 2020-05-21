import datajoint as dj
from .. import lab, acquisition, processing

schema = dj.schema('churchland_pacman')

# -------------------------------------------------------------------------------------------------------------------------------
# LEVEL 0
# -------------------------------------------------------------------------------------------------------------------------------

@schema 
class ArmPosture(dj.Lookup):
    definition = """
    # Arm posture
    -> lab.Monkey
    posture_id : tinyint unsigned # unique posture ID number
    ---
    elbow_angle : tinyint unsigned # elbow flexion angle in degrees (0 = fully flexed)
    shoulder_angle : tinyint unsigned # shoulder flexion angle in degrees (0 = arm by side)
    """

@schema
class SimulinkState(dj.Lookup):
    definition = """
    # Simulink Stateflow state IDs and names
    state_id : tinyint unsigned # unique task state ID number
    ---
    state_name : varchar(64) # task state name
    """    
    
@schema
class Task(dj.Imported):
    definition = """
    # Speedgoat task data parser
    -> acquisition.SpeedgoatRecording
    ---
    """
    
    class Condition(dj.Part):
        definition = """
        # Condition data
        -> master
        targ_id: smallint unsigned # target condition ID
        stim_id: smallint unsigned # stimulation condition ID
        ---
        force_polarity : tinyint # indicates whether pushing (polarity = 1) or pulling (polarity = -1) moves Pac-Man upwards
        force_max : tinyint unsigned # maximum force [Newtons]
        force_offset : decimal(5,4) # force offset to compensate for arm weight [Newtons]
        target_type : char(3) # type code
        target_offset : decimal(5,4) # offset
        target_amplitude : decimal(5,4) # amplitude
        target_duration : decimal(5,4) # duration
        target_frequency1 : decimal(5,4) # primary frequency (initial, for chirp forces)
        target_frequency2 : decimal(5,4) # secondary frequency (final, for chirp forces)
        target_power : decimal(5,4) # power exponent
        target_pad : decimal(5,4) # pad duration
        stim_current : smallint unsigned # stim current (uA)
        stim_electrode : smallint unsigned # stim electrode number
        stim_polarity : tinyint unsigned # stim polarity
        stim_pulses : tinyint unsigned # number of pulses in stim train
        stim_width1 : smallint unsigned # first pulse duration (us)
        stim_width2 : smallint unsigned # second pulse duration (us)
        stim_interphase : smallint unsigned # interphase duration (us)
        stim_frequency : smallint unsigned # stim frequency (Hz)
        """

    class Trial(dj.Part):
        definition = """
        # Trial data
        -> master
        trial_number : smallint unsigned # trial number (within session)
        ---
        -> Task.Condition
        save_tag : tinyint unsigned # save tag
        valid_trial : tinyint unsigned # is valid trial (1=yes, 0=no)
        successful_trial : tinyint unsigned # is successful trial (1=yes, 0=no)
        simulation_time : longblob # absolute simulation time
        task_state : longblob # task state IDs
        force_raw_online : longblob # amplified output of load cell
        force_filt_online : longblob # online (boxcar) filtered and normalized force used to control Pac-Man
        stim : longblob # ICMS delivery
        reward : longblob # reward delivery
        photobox : longblob # photobox signal
        """
    
@schema
class TrialAlignment(dj.Imported):
    definition = """
    -> acquisition.SyncChannel
    trial_number : smallint unsigned # trial number (within session)
    ---
    alignment_index : int unsigned # alignment index (in Speedgoat time base)
    speedgoat_alignment : longblob # alignment indices for Speedgoat data
    ephys_alignment : longblob # alignment indices for Ephys data
    """    

# -------------------------------------------------------------------------------------------------------------------------------
# LEVEL 1
# -------------------------------------------------------------------------------------------------------------------------------

@schema
class Force(dj.Computed):
    definition = """
    # Single trial force
    -> Task.Trial
    -> TrialAlignment
    ---
    force_raw = null : longblob # aligned raw (online) force [Volts]
    force_filt = null : longblob # offline filtered, aligned, and calibrated force [Newtons]
    """

@schema
class MotorUnitSpikes(dj.Computed):
    definition = """
    # Aligned motor unit trial spikes
    -> processing.MotorUnit.SessionSpikes
    -> TrialAlignment
    ---
    motor_unit_spikes : longblob # trial-aligned spike raster (logical)
    """
    
@schema
class NeuronSpikes(dj.Computed):
    definition = """
    # Aligned neuron trial spikes
    -> processing.Neuron.SessionSpikes
    -> TrialAlignment
    ---
    neuron_spikes : longblob # trial-aligned spike raster (logical)
    """
    
    
@schema
class SessionBlock(dj.Manual):
    definition = """
    # Set of save tags and arm postures for conducting analyses
    -> acquisition.Session
    block_id : tinyint unsigned # block ID
    ---
    -> ArmPosture
    save_tags : blob # vector of save tags assigned to group
    """
    
# -------------------------------------------------------------------------------------------------------------------------------
# LEVEL 2
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
class MotorUnitPsth(dj.Computed):
    definition = """
    # Peri-stimulus time histogram
    -> processing.MotorUnit.SessionSpikes
    -> SessionBlock
    ---
    motor_unit_psth : longblob # psth
    """
    
@schema
class MotorUnitRate(dj.Computed):
    definition = """
    # Aligned motor unit trial firing rate
    -> MotorUnitSpikes
    ---
    motor_unit_rate : longblob # trial-aligned firing rate [Hz]
    """

@schema
class NeuronPsth(dj.Computed):
    definition = """
    # Peri-stimulus time histogram
    -> processing.Neuron.SessionSpikes
    -> SessionBlock
    ---
    neuron_psth : longblob # psth
    """    
    
@schema
class NeuronRate(dj.Computed):
    definition = """
    # Aligned neuron trial firing rate
    -> NeuronSpikes
    ---
    neuron_rate : longblob # trial-aligned firing rate [Hz]
    """
    
@schema
class TrialBlock(dj.Computed):
    definition = """
    # Session block ID for each trial
    -> Task.Trial
    -> SessionBlock
    ---
    """    
    
# -------------------------------------------------------------------------------------------------------------------------------
# LEVEL 3
# ------------------------------------------------------------------------------------------------------------------------------- 

@schema 
class GoodTrial(dj.Computed):
    definition = """
    # Trials that meet behavior quality thresholds
    -> BehaviorQuality
    ---
    """