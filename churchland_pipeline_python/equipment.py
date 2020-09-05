import datajoint as dj

schema = dj.schema('churchland_common_equipment')

# -------------------------------------------------------------------------------------------------------------------------------
# LEVEL 0
# -------------------------------------------------------------------------------------------------------------------------------

@schema
class EquipmentCategory(dj.Lookup):
    definition = """
    equipment_category: varchar(32)
    """

    contents = [
        ['bioamplifier'],
        ['chamber'],
        ['graphics'],
        ['load cell'],
        ['motion tracker'],
        ['neural signal processor'],
        ['neural stimulator'],
        ['spike sorter'],
        ['task controller']
    ]

@schema
class Parameter(dj.Lookup):
    definition = """
    parameter:             varchar(32)  # parameter name
    ---
    parameter_description: varchar(255) # additional parameter details, units, etc.
    """

    contents = [
        ['force capacity', 'maximum force capacity (Newtons)'],
        ['voltage output', 'calibrated output signal (Volts)']
    ]

@schema
class ProbeModel(dj.Lookup):
    definition = """
    # Model and geometry of an electrophysiology probe
    probe_model:          varchar(32)          # e.g. Utah, Neuropixels
    ---
    probe_type:           enum('neural','emg') # type of data used to record
    probe_manufacturer:   varchar(255)         # manufacturer of the probe
    probe_version = null: float                # version number
    probe_manual = null:  varchar(255)         # path to probe manual
    """

    class Shank(dj.Part):
        definition = """
        -> master
        shank:        int unsigned # shank index
        ---
        shank_x:      float        # (um) x-coordinate of each shank, relative to the shank at the corner/end of the base (x = 0)
        shank_y:      float        # (um) y-coordinate of each shank, relative to the shank at the corner/end of the base (y = 0)
        shank_width:  float        # (mm)
        shank_length: float        # (mm)
        """

    class Electrode(dj.Part):
        definition = """
        # Recording sites
        -> master.Shank
        electrode:                 int unsigned # electrode index
        ---
        electrode_x:               float        # (um) x-coordinate of the electrode, relative to the bottom tip of the shank (x = 0)
        electrode_z:               float        # (um) z-coordinate of the electrode, relative to the bottom tip of the shank (z = 0)
        electrode_diameter = null: float        # (um)
        """

# -------------------------------------------------------------------------------------------------------------------------------
# LEVEL 1
# -------------------------------------------------------------------------------------------------------------------------------

@schema
class Hardware(dj.Lookup):
    definition = """
    hardware:                       varchar(32)   # hardware name
    ---
    -> EquipmentCategory.proj(hardware_category = 'equipment_category')
    hardware_model:                 varchar(255)
    hardware_manufacturer:          varchar(255)
    hardware_manufacturer_location: varchar(255)
    hardware_manual = null:         varchar(255)  # manual file path (replace with attachment)
    """

    class Parameter(dj.Part):
        definition = """
        -> master
        -> Parameter
        ---
        parameter_value: float
        """

    contents = [
        ['Speedgoat',     'task controller',         'Performance real-time target machine', 'Speedgoat GmbH',              'Liebefeld, Switzerland',    ''],
        ['Cerebus',       'neural signal processor', 'LB 0028',                              'Blackrock Microsystems',      'Salt Lake City, UT',        '/srv/locker/churchland/General/equipment-manuals/CerebusNSP.pdf'],
        ['CereStim',      'neural stimulator',       'LB 0314',                              'Blackrock Microsystems',      'Salt Lake City, UT',        '/srv/locker/churchland/General/equipment-manuals/CerestimR96.pdf'],
        ['StimPulse',     'neural stimulator',       '55-60-0',                              'FHC, Inc',                    'Bowdoin, ME',               '/srv/locker/churchland/General/equipment-manuals/StimPulse.pdf'],
        ['Polaris',       'motion tracker',          'Spectra',                              'Northern Digital',            'Waterloo, Ontario, Canada', '/srv/locker/churchland/General/equipment-manuals/Polaris.pdf'],
        ['5lb Load Cell', 'load cell',               'LRM200',                               'FUTEK',                       'Irvine, CA',                '/srv/locker/churchland/General/equipment-manuals/LRM200_5lb.pdf'],
        ['DAM8',          'bioamplifier',            'ISO-DAM8A',                            'World Precision Instruments', 'Sarasota, FL',              '/srv/locker/churchland/General/equipment-manuals/ISODAM8A.pdf'],
        ['CILUX chamber', 'chamber',                 '6-IAM-J0',                             'Crist Instrument Co Inc',     'Hagerstown, MD',            '']
    ]

@schema
class Probe(dj.Lookup):
    definition = """
    -> ProbeModel
    probe_id:       int unsigned # unique ID number
    ---
    probe_serial:   varchar(255) # serial number
    """

@schema
class Software(dj.Lookup):
    definition = """
    software:                       varchar(32)   # software name
    software_version:               varchar(32)
    ---
    -> EquipmentCategory.proj(software_category = 'equipment_category')
    software_manufacturer:          varchar(255)
    software_manufacturer_location: varchar(255)
    software_manual = null:         varchar(255)  # manual file path (replace with attachment)
    """

    class Parameter(dj.Part):
        definition = """
        -> master
        -> Parameter
        ---
        parameter_value: float
        """

    contents = [
        ['Simulink',     '',      'task controller',  'MathWorks',          'Natick, MA',        ''],
        ['Plexon OFS',   '4.5.0', 'spike sorter',     'Plexon',             'Dallas, TX',        ''],
        ['KiloSort',     '1.0',   'spike sorter',     'Cortexlab',          'UCL',               ''],
        ['Unity 3D',     '',      'graphics',         'Unity Technologies', 'San Francisco, CA', ''],
        ['Psychtoolbox', '3.0',   'graphics',         'open source',        '',                  '']
    ]