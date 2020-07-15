import datajoint as dj

schema = dj.schema('churchland_common_equipment')

# -------------------------------------------------------------------------------------------------------------------------------
# LEVEL 0
# -------------------------------------------------------------------------------------------------------------------------------

@schema
class Type(dj.Lookup):
    definition = """
    equipment_type: varchar(32)
    ---
    equipment_category: varchar(32)
    """

    contents = [
        ['load cell',                'behavior'],
        ['motion tracker',           'behavior'],
        ['task controller hardware', 'behavior'],
        ['task controller software', 'behavior'],
        ['bioamplifier',             'ephys'],
        ['emg electrode',            'ephys'],
        ['microdrive',               'ephys'],
        ['neural electrode',         'ephys'],
        ['neural signal processor',  'ephys'],
        ['stimulator',               'ephys'],
        ['chamber',                  'surgery'],
    ]

# -------------------------------------------------------------------------------------------------------------------------------
# LEVEL 1
# -------------------------------------------------------------------------------------------------------------------------------

@schema
class Equipment(dj.Lookup):
    definition = """
    -> Type
    equipment_id: tinyint unsigned
    ---
    equipment_name:                  varchar(255)
    equipment_model:                 varchar(255)
    equipment_manufacturer:          varchar(255)
    equipment_manufacturer_location: varchar(255)
    equipment_manual = null:         varchar(255) # manual file path (replace with attachment)
    equipment_notes = null:          varchar(4095)
    """

    contents = [
        ['load cell',                0, 'Miniature S-Beam Jr. Load Cell', 'LRM200', 'FUTEK', 'Irvine, CA', '/srv/locker/churchland/General/equipment-manuals/LRM200_5lb.pdf', ''],
        ['motion tracker',           0, 'Polaris', 'Spectra', 'Northern Digital', 'Waterloo, Ontario, Canada', '/srv/locker/churchland/General/equipment-manuals/Polaris.pdf', ''],
        ['task controller hardware', 0, 'Speedgoat', 'Performance real-time target machine', 'Speedgoat GmbH', 'Liebefeld, Switzerland', '', ''],
        ['task controller software', 0, 'Simulink', '', 'MathWorks', 'Natick, MA', '', ''],
        ['bioamplifier',             0, 'Isolated, Low Noise Bioamplifier Single Channel Module', 'ISO-DAM8A', 'World Precision Instruments', 'Sarasota, FL', '/srv/locker/churchland/General/equipment-manuals/ISODAM8A.pdf', ''],
        ['emg electrode',            0, 'Hook-Wire, paired', '019-475400', 'Natus Medical Inc', 'Pleasanton, CA', '', ''],
        ['emg electrode',            1, 'Hook-Wire, paired, trimmed', '019-475400 (modified)', 'Natus Medical Inc', 'Pleasanton, CA', '', 'Custom modification of stock electrodes. Trimmed the ends of each wire to 1 mm.'],
        ['emg electrode',            2, 'Hook-Wire, quadrifilar', '019-475400 (modified)', 'Natus Medical Inc', 'Pleasanton, CA', '', 'Custom modification of stock electrodes. Trimmed the ends of one pair of wires to 1 mm and another to 0.5 mm. Threaded both pairs into one needle such that the ends of one pair protruded from the needle by 1 mm and 8 mm and the second pair protruded by 3.25 mm and 5.25 mm.'],
        ['microdrive',               0, 'Oil Hydraulic Micromanipulator', 'MO-97A', 'Narishige Group', 'Tokyo, Japan', '', ''],
        ['neural electrode',         0, 'V-Probe', '24-channel', 'Plexon', 'Dallas, TX', '/srv/locker/churchland/General/equipment-manuals/PlexonProbes.pdf', ''],
        ['neural electrode',         1, 'S-Probe', '32-channel', 'Plexon', 'Dallas, TX', '/srv/locker/churchland/General/equipment-manuals/PlexonProbes.pdf', ''],
        ['neural electrode',         2, 'Neuropixels', '128-channel', 'IMEC', 'Leuven, Belgium', '', ''],
        ['neural electrode',         3, 'Utah Array', 'CerePort (chronic)', 'Blackrock Microsystems', 'Salt Lake City, UT', '', ''],
        ['neural signal processor',  0, 'Cerebus', 'LB 0028', 'Blackrock Microsystems', 'Salt Lake City, UT', '/srv/locker/churchland/General/equipment-manuals/CerebusNSP.pdf', ''],
        ['stimulator',               0, 'CereStim R96', 'LB 0314', 'Blackrock Microsystems', 'Salt Lake City, UT', '/srv/locker/churchland/General/equipment-manuals/CerestimR96.pdf', ''],
        ['stimulator',               1, 'neuro/Craft StimPulse', '55-60-0', 'FHC, Inc', 'Bowdoin, ME', '/srv/locker/churchland/General/equipment-manuals/StimPulse.pdf', ''],
        ['chamber',                  0, 'CILUX Pin Style chamber', '6-IAM-J0', 'Crist Instrument Co Inc', 'Hagerstown, MD', '', ''],
    ]

