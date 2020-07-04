import datajoint as dj
from ... import lab, acquisition, processing

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
    
    contents = [
        ['Cousteau', 1, 90, 65],
        ['Cousteau', 2, 90, 40],
        ['Cousteau', 3, 90, 75]
    ]

@schema
class ForceParams(dj.Lookup):
    definition = """
    # Force parameters for Pac-Man task
    force_id : smallint unsigned # ID number
    ---
    force_max : tinyint unsigned # maximum force [Newtons]
    force_offset : decimal(5,4) # force offset to compensate for arm weight [Newtons]
    force_direction : enum("push","pull") # indicates whether pushing or pulling moves Pac-Man upwards onscreen
    """
    
@schema
class StimParams(dj.Lookup):
    definition = """
    # Cerestim parameters
    stim_id : smallint unsigned # ID number
    ---
    stim_current : smallint unsigned # stim current (uA)
    stim_electrode : smallint unsigned # stim electrode number
    stim_polarity : tinyint unsigned # stim polarity
    stim_pulses : tinyint unsigned # number of pulses in stim train
    stim_width1 : smallint unsigned # first pulse duration (us)
    stim_width2 : smallint unsigned # second pulse duration (us)
    stim_interphase : smallint unsigned # interphase duration (us)
    stim_frequency : smallint unsigned # stim frequency (Hz)
    """

@schema
class TargetParams(dj.Lookup):
    definition = """
    # Target force profiles for Pac-Man task
    target_type : enum("STA", "RMP", "SIN", "CHP")
    target_id : smallint unsigned # ID number
    ---
    target_duration : decimal(5,4) # target duration [seconds]
    target_offset : decimal(5,4) # offset from baseline [proportion playable window]
    target_pad : decimal(5,4) # duration of "padding" dots leading into and out of target [seconds]
    """
    
    class Static(dj.Part):
        definition = """
        # Static force profile (type code: STA)
        -> master
        ---
        """
        
    class Ramp(dj.Part):
        definition = """
        # Linear ramp force profile (type code: RMP)
        -> master
        ---
        target_amplitude : decimal(5,4) # target amplitude [proportion playable window]
        """
        
    class Sine(dj.Part):
        definition = """
        # Sinusoidal (single-frequency) force profile (type code: SIN)
        -> master
        ---
        target_amplitude : decimal(5,4) # target amplitude [proportion playable window]
        target_frequency : decimal(5,4) # sinusoid frequency [Hz]
        """
        
    class Chirp(dj.Part):
        definition = """
        # Chirp force profile (type code: CHP)
        -> master
        ---
        target_amplitude : decimal(5,4) # target amplitude [proportion playable window]
        target_frequency_init : decimal(5,4) # initial frequency [Hz]
        target_frequency_final : decimal(5,4) # final frequency [Hz]
        """
        
    # power function, sum of sines, triangle waves...
    
@schema
class TaskState(dj.Lookup):
    definition = """
    # Simulink Stateflow task state IDs and names
    task_state_id : tinyint unsigned # task state ID number
    ---
    task_state_name : varchar(255) # unique task state name
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
        -> ForceParams
        -> TargetParams
        -> StimParams
        """

    class Trial(dj.Part):
        definition = """
        # Trial data
        -> master
        trial_number : smallint unsigned # trial number (within session)
        ---
        -> Behavior.Condition
        save_tag : tinyint unsigned # save tag
        successful_trial : tinyint unsigned # is successful trial (1=yes, 0=no)
        simulation_time : longblob # absolute simulation time
        task_state : longblob # task state IDs
        force_raw_online : longblob # amplified output of load cell
        force_filt_online : longblob # online (boxcar) filtered and normalized force used to control Pac-Man
        stim : longblob # TTL signal indicating the delivery of a stim pulse
        reward : longblob # TTL signal indicating the delivery of juice reward
        photobox : longblob # photobox signal
        """
        
    def make(self, key):
        
        # locate summary file (temporary until behavior recording filepath attribute update)
        sgPath = rawPath + str(key['session_date']) + '/speedgoat/'
        sgFiles = sorted(list(os.listdir(sgPath)))
        summaryFile = [x for x in sgFiles if re.search('.*\.summary',x) is not None][0]
        
        # speedgoat prefix
        sgPrefix = sgPath + re.search('(.*)\.summary',summaryFile).group(1)
        
        # check for new task states
        
        # update lookup tables
        
        # populate session condition and trial tables

@schema
class AlignmentState(dj.Lookup):
    definition = """
    # Task state IDs used to align trials
    -> TaskState
    ---
    """
    
    contents = [
        [5]
    ]

@schema
class SessionBlock(dj.Manual):
    definition = """
    # Set of save tags and arm postures for conducting analyses
    -> acquisition.Session
    block_id : tinyint unsigned # block ID
    ---
    -> ArmPosture
    """
    
    class SaveTag(dj.Part):
        definition = """
        # Block save tags
        -> master
        -> acquisition.Session.SaveTag
        """

# -------------------------------------------------------------------------------------------------------------------------------
# LEVEL 2
# -------------------------------------------------------------------------------------------------------------------------------

@schema
class MotorUnitPsth(dj.Computed):
    definition = """
    # Peri-stimulus time histogram
    -> processing.MotorUnit
    -> Behavior.Condition
    -> SessionBlock
    ---
    motor_unit_psth : longblob # psth
    -> processing.Filter
    """

@schema
class NeuronPsth(dj.Computed):
    definition = """
    # Peri-stimulus time histogram
    -> processing.Neuron
    -> Behavior.Condition
    -> SessionBlock
    ---
    neuron_psth : longblob # psth
    -> processing.Filter
    """

@schema
class TrialAlignment(dj.Imported):
    definition = """
    # Alignment indices for each behavior trial
    -> AlignmentState
    -> Behavior.Trial
    ---
    -> acquisition.EphysRecording.Electrode
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
    
@schema
class TrialBlock(dj.Computed):
    definition = """
    # Session block ID for each trial
    -> Behavior.Trial
    -> SessionBlock
    ---
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