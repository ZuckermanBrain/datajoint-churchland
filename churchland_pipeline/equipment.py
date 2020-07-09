import datajoint as dj
import numpy as np

schema = dj.schema('churchland_common_equipment')

@schema
class Behavior(dj.Lookup):
    definition = """
    # Equipment for recording behavior
    item_id: tinyint unsigned
    """
    
    #contents = np.arange(1).tolist()

    class LoadCell(dj.Part):
        definition = """
        # Load cell (force sensor)
        -> master
        loadcell:                       varchar(16) # nickname
        ---
        loadcell_name:                  varchar(255) # full name
        loadcell_model:                 varchar(255)
        loadcell_manufacturer:          varchar(255)
        loadcell_manufacturer_location: varchar(255)
        loadcell_capacity:              double # maximum force capacity [Newtons]
        loadcell_output:                double # calibrated maximum output [Volts]
        loadcell_manual = null:         varchar(255) # manual file path (replace with attachment)
        """

        """
        contents = [
            [0, 'Futek5lb', 'Miniature S-Beam Jr. Load Cell', 'LRM200', 'FUTEK', 'Irvine, CA', 22.2411, 5.095, '/srv/locker/churchland/General/equipment-manuals/LRM200_5lb.pdf']
        ]
        """

    class MotionTracker(dj.Part):
        definition = """
        # Motion tracking systems
        -> master
        motion_tracker:                       varchar(16) # nickname
        ---
        motion_tracker_name:                  varchar(255) # full name
        motion_tracker_model:                 varchar(255)
        motion_tracker_manufacturer:          varchar(255)
        motion_tracker_manufacturer_location: varchar(255)
        motion_tracker_manual = null:         varchar(255) # manual file path (replace with attachment)
        """

        """
        contents = [
            [0, 'Polaris', 'Polaris', 'Spectra', 'Northern Digital', 'Waterloo, Ontario, Canada', '/srv/locker/churchland/General/equipment-manuals/Polaris.pdf']
        ]
        """

    class TaskController(dj.Part):
        definition = """
        # Hardware and software used for task control
        -> master
        task_controller:                                varchar(16) # nickname
        ---
        task_controller_hardware:                       varchar(255) # full hardware name
        task_controller_hardware_manufacturer:          varchar(255)
        task_controller_hardware_manufacturer_location: varchar(255)
        task_controller_hardware_manual = null:         varchar(255) # hardare manual file path (replace with attachment)
        task_controller_software:                       varchar(255) # full software name
        task_controller_software_manufacturer:          varchar(255)
        task_controller_software_manufacturer_location: varchar(255)
        task_controller_software_manual = null:         varchar(255) # software manual file path (replace with attachment)
        """

        """
        contents = [
            [0, 'Speedgoat', 'Performance real-time target machine', 'Speedgoat GmbH', 'Liebefeld, Switzerland', '', 'xPC Target', 'MathWorks', 'Natick, MA', '']
        ]
        """

@schema
class Ephys(dj.Lookup):
    definition = """
    # Equipment for recording electrophysiological data
    item_id: tinyint unsigned
    """

    #contents = np.arange(4).tolist()

    class Bioamplifier(dj.Part):
        definition = """
        # Bioamplifier
        -> master
        bioamplifier:                       varchar(16) # nickname
        ---
        bioamplifier_name:                  varchar(255) # full name
        bioamplifier_model:                 varchar(255)
        bioamplifier_manufacturer:          varchar(255)
        bioamplifier_manufacturer_location: varchar(255)
        bioamplifier_manual = null:         varchar(255) # manual file path (replace with attachment)
        """

        """
        contents = [
            [0, 'DAM8', 'Isolated, Low Noise Bioamplifier Single Channel Module', 'ISO-DAM8A', 'World Precision Instruments', 'Sarasota, FL', '/srv/locker/churchland/General/equipment-manuals/ISODAM8A.pdf']
        ]
        """

    class EmgElectrode(dj.Part):
        definition = """
        -> master
        emg_electrode:                       varchar(16) # nickname
        ---
        emg_electrode_name:                  varchar(255) # full name
        emg_electrode_model:                 varchar(255)
        emg_electrode_manufacturer:          varchar(255)
        emg_electrode_manufacturer_location: varchar(255)
        emg_electrode_channel_count:         smallint unsigned # total number of active recording channels on the electrode
        emg_electrode_manual = null:         varchar(255) # manual file path (replace with attachment)
        """

        """
        contents = [
            [0, 'FineWire', 'Hook-Wire, paired', '019-475400', 'Natus Medical Inc', 'Pleasanton, CA', 1, ''],
        ]
        """

    class EmgElectrodeMod(dj.Part):
        definition = """
        # Custom electrode modification
        -> Ephys.EmgElectrode
        mod_id:                 tinyint unsigned
        ---
        mod_name:               varchar(255) # short-hand nickname for modification
        mod_channel_count:      smallint unsigned # updated channel count
        mod_description = null: varchar(1024) # modification description
        """

        """
        contents = [
            [0, 'FineWire', 0, 'stock', 1, ''],
            [0, 'FineWire', 1, 'trimmed', 1, 'Trimmed stripped ends of each wire from 2 mm to 1 mm.'],
            [0, 'FineWire', 2, 'quad', 2, 'Trimmed stripped ends of one pair of wires to 1 mm and a second pair to 0.5 mm. Threaded both pairs into the same needle such that the first pair of wires protruded 1 mm and 8 mm and the second pair protruded 3.25 mm and 5.25 mm from the end of the needle.']
        ]
        """

    class Microdrive(dj.Part):
        definition = """
        # Neural microdrives
        -> master
        microdrive:                       varchar(16) # nickname
        ---
        microdrive_name:                  varchar(255) # full name
        microdrive_model:                 varchar(255)
        microdrive_manufacturer:          varchar(255)
        microdrive_manufacturer_location: varchar(255)
        microdrive_manual = null:         varchar(255) # manual file path (replace with attachment)
        """

        """
        contents = [
            [0, 'Narishige', 'Oil Hydraulic Micromanipulator', 'MO-97A', 'Narishige Group', 'Tokyo, Japan', '']
        ]
        """

    class NeuralElectrode(dj.Part):
        definition = """
        -> master
        neural_electrode:                       varchar(16) # nickname
        ---
        neural_electrode_name:                  varchar(255) # full name
        neural_electrode_model:                 varchar(255) 
        neural_electrode_manufacturer:          varchar(255)
        neural_electrode_manufacturer_location: varchar(255)
        neural_electrode_type:                  enum('probe', 'array') # linear probe or microelectrode array
        neural_electrode_channel_count:         int unsigned # total number of active recording channels on the electrode
        neural_electrode_manual = null:         varchar(255) # manual file path (replace with attachment)
        """

        """
        contents = [
            [0, 'V24', 'V-Probe', '24-channel', 'Plexon', 'Dallas, TX', 'probe', 24, '/srv/locker/churchland/General/equipment-manuals/PlexonProbes.pdf'],
            [1, 'S32', 'S-Probe', '32-channel', 'Plexon', 'Dallas, TX', 'probe', 32, '/srv/locker/churchland/General/equipment-manuals/PlexonProbes.pdf'],
            [2, 'Neupix128', 'Neuropixels', '128-channel', 'IMEC', 'Leuven, Belgium', 'probe', 128, ''],
            [3, 'Utah96', 'Utah Array', 'CerePort (chronic)', 'Blackrock Microsystems', 'Salt Lake City, UT', 'array', 96, ''],
        ]
        """

    class NeuralSignalProcessor(dj.Part):
        definition = """
        # Neural signal processor (NSP)
        -> master
        nsp:                       varchar(16) # nickname
        ---
        nsp_name:                  varchar(255) # full name
        nsp_model:                 varchar(255)
        nsp_manufacturer:          varchar(255)
        nsp_manufacturer_location: varchar(255)
        nsp_manual = null:         varchar(255) # manual file path (replace with attachment)
        """

        """
        contents = [
            [0, 'Blackrock', 'Cerebus Neural Signal Processor', 'LB 0028', 'Blackrock Microsystems', 'Salt Lake City, UT', '/srv/locker/churchland/General/equipment-manuals/CerebusNSP.pdf']
        ]
        """

    class Stimulator(dj.Part):
        definition = """
        # Stimulation system
        -> master
        stimulator:                       varchar(16) # nickname
        ---
        stimulator_name:                  varchar(255) # full name
        stimulator_model:                 varchar(255)
        stimulator_manufacturer:          varchar(255)
        stimulator_manufacturer_location: varchar(255)
        stimulator_manual = null:         varchar(255) # manual file path (replace with attachment)
        """

        """
        contents = [
            [0, 'Cerestim', 'CereStim R96', 'LB 0314', 'Blackrock Microsystems', 'Salt Lake City, UT', '/srv/locker/churchland/General/equipment-manuals/CerestimR96.pdf'],
            [1, 'Stimpulse', 'neuro/Craft StimPulse', '55-60-0', 'FHC, Inc', 'Bowdoin, ME', '/srv/locker/churchland/General/equipment-manuals/StimPulse.pdf']
        ]
        """

@schema
class Surgery(dj.Lookup):
    definition = """
    # Equipment for surgeries and procedures
    item_id: tinyint unsigned
    """

    #contents = np.arange(1).tolist()

    class Chamber(dj.Part):
        definition = """
        # Neural recording chamber
        -> master
        chamber:                       varchar(16) # nickname
        ---
        chamber_name:                  varchar(255) # full name
        chamber_model:                 varchar(255)
        chamber_manufacturer:          varchar(255)
        chamber_manufacturer_location: varchar(255)
        chamber_manual = null:         varchar(255) # manual file path (replace with attachment)
        """

        """
        contents = [
            [0, 'Crist', 'CILUX Pin Style chamber', '6-IAM-J0', 'Crist Instrument Co Inc', 'Hagerstown, MD', ''],
        ]
        """



