"""Equipment schema.

This module contains class definitions for lab equipment (hardware and software).

Coordinate system: x (+/-, right/left onscreen); y (+/-, up/down onscreen); z (+/-, into/out of screen)
"""

import datajoint as dj
import re
import numpy as np
from . import lab
from .utilities import datajointutils
from decimal import Decimal
from typing import List, Tuple

schema = dj.schema(dj.config.get('database.prefix') + 'churchland_common_equipment')

# =======
# LEVEL 0
# =======

@schema
class ElectrodeGeometry(dj.Lookup):
    definition = """
    # Geometry of an electrode, defined by its base and tip, oriented orthogonal to the x-y plane
    electrode_geometry_id:                smallint unsigned                 # electrode geometry ID number
    ---
    electrode_base_shape:                 enum('cuboid', 'cylinder')        # electrode base shape
    electrode_base_x_length:              decimal(9,9) unsigned             # electrode base x-axis length (m)
    electrode_base_y_length:              decimal(9,9) unsigned             # electrode base y-axis length (m)
    electrode_base_z_length = 0:          decimal(9,9) unsigned             # electrode base z-axis length (m)
    electrode_base_insulation_length = 0: decimal(9,9) unsigned             # electrode base insulation length, starting from base top (m)
    electrode_base_rotation = 0:          decimal(9,9) unsigned             # electrode base rotation in the x-y plane (multiples of 2*pi)
    electrode_tip_profile = 'linear':     enum('linear', 'curved', 'sharp') # electrode tip profile
    electrode_tip_z_length = 0:           decimal(9,9) unsigned             # electrode tip z-axis length (m)
    electrode_tip_insulation_length = 0:  decimal(9,9) unsigned             # electrode tip insulation length, starting from tip bottom (m)
    """

    contents = [
        #id   |base shape |base-x   |base-y   |base-z    |base ins. |base rot. |tip prof. |tip-z   |tip ins.
        [0,    'cuboid',   12e-6,    12e-6,    0,         0,         0,         'linear',  0,       0],        # flat square (e.g., Neuropixels)
        [1,    'cylinder', 15e-6,    15e-6,    0,         0,         0,         'linear',  0,       0],        # flat circle (e.g., S-Probes)
        [2,    'cylinder', 100e-6,   100e-6,   0,         0,         0,         'sharp',   1.5e-3,  0],        # cone (e.g., Utah array)
        [3,    'cylinder', 100e-6,   100e-6,   139.5e-3,  129.5e-3,  0,         'sharp',   0.5e-3,  0.4e-3],   # sharp cylinder w/ insulation (e.g., FHC sharp electrode)
        [4,    'cuboid',   50e-6,    50e-6,    123e-3,    0,         0,         'linear',  2e-3,    0],        # blunt cylinder w/ insulation (e.g., Natus hook-wire stock)
        [5,    'cuboid',   50e-6,    50e-6,    120e-3,    0,         0,         'linear',  5e-3,    3e-3],     # blunt cylinder w/ insulation (e.g., Natus hook-wire stock)
        [6,    'cuboid',   50e-6,    50e-6,    124e-3,    0,         0,         'linear',  1e-3,    0],        # blunt cylinder w/ insulation (Natus hook-wire QF 1,1)
        [7,    'cuboid',   50e-6,    50e-6,    117e-3,    0,         0,         'linear',  8e-3,    7e-3],     # blunt cylinder w/ insulation (Natus hook-wire QF 1,2)
        [8,    'cuboid',   50e-6,    50e-6,    121.75e-3, 0,         0,         'linear',  3.25e-3, 2.75e-3],  # blunt cylinder w/ insulation (Natus hook-wire QF 2,1)
        [9,    'cuboid',   50e-6,    50e-6,    119.75e-3, 0,         0,         'linear',  5.25e-3, 4.75e-3],  # blunt cylinder w/ insulation (Natus hook-wire QF 2,2)
        [10,   'cuboid',   50e-6,    50e-6,    123e-3,    0,         0,         'linear',  1e-3,    0],        # blunt cylinder w/ insulation (e.g., Natus hook-wire clipped)
        [11,   'cuboid',   50e-6,    50e-6,    120e-3,    0,         0,         'linear',  4e-3,    3e-3]      # blunt cylinder w/ insulation (e.g., Natus hook-wire clipped)
    ]


@schema
class EquipmentCategory(dj.Lookup):
    definition = """
    equipment_category: varchar(32) # equipment category name
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
class EquipmentParameter(dj.Lookup):
    definition = """
    equipment_parameter:                  varchar(32)  # equipment parameter name
    ---
    equipment_parameter_units = '':       varchar(32)  # equipment parameter units
    equipment_parameter_description = '': varchar(255) # equipment parameter description
    """

    contents = [
        ['force capacity', 'N', 'maximum force capacity'],
        ['voltage output', 'V', 'calibrated output signal'],
        ['diameter',       'm', 'equipment diameter']
    ]


# =======
# LEVEL 1
# =======

@schema
class ElectrodeArrayModel(dj.Lookup):
    definition = """
    # Model of an electrode array
    electrode_array_model:              varchar(32)            # electrode array model name
    electrode_array_model_version:      varchar(32)            # electrode array model version
    ---
    electrode_array_model_manufacturer: varchar(255)           # electrode array model manufacturer
    recording_tissue:                   enum('brain','muscle') # tissue type array used to record from
    invasive:                           bool                   # whether array is for invasive (True) or surface (False) recordings
    """

    class Shank(dj.Part):
        definition = """
        # Electrode array shank, oriented orthogonal to the x-z plane (up/down onscreen)
        -> master
        shank_idx:            int unsigned # shank index
        ---
        shank_x = 0:          decimal(9,9) # shank center x-coordinate relative to origin (m)
        shank_y = 0:          decimal(9,9) # shank center y-coordinate relative to origin (m)
        shank_z = 0:          decimal(9,9) # shank center z-coordinate relative to origin (m)
        shank_x_length = 0:   decimal(9,9) # length of shank along x-axis (m)
        shank_y_length = 0:   decimal(9,9) # length of shank along y-axis (m)
        shank_z_length = 0:   decimal(9,9) # length of shank along z-axis (m)
        shank_tip_length = 0: decimal(9,9) # length of shank tip along y-axis (m) (not additive with shank base length)
        """

    class Electrode(dj.Part):
        definition = """
        -> master.Shank
        electrode_idx: int unsigned # electrode index
        ---
        electrode_x:   decimal(9,9) # electrode center x-coordinate relative to shank midline (m)
        electrode_y:   decimal(9,9) # electrode center y-coordinate relative to shank tip (m)
        -> ElectrodeGeometry
        """

    contents = [
        #model name    |model version |model manufacturer       |recording tissue |invasive
        ['Hook-Wire',   'paired',      'Natus Medical Inc.',     'muscle',         True],
        ['Hook-Wire',   'quad',        'custom',                 'muscle',         True],
        ['Hook-Wire',   'clipped',     'custom',                 'muscle',         True],
        ['Neuropixels', 'nhp demo',    'IMEC',                   'brain',          True],
        ['S-Probe',     '32 chan',     'Plexon',                 'brain',          True],
        ['V-Probe',     '24 chan',     'Plexon',                 'brain',          True],
        ['Utah',        '96 chan',     'Blackrock Microsystems', 'brain',          True]
    ]

    def build(self, verbose: bool=False):

        # build arrays without electrodes
        key_source = (self - self.Electrode).fetch('KEY')

        for array_key in key_source:

            if verbose:
                print('Building {} {}'.format(
                    array_key['electrode_array_model'], 
                    array_key['electrode_array_model_version'])
                )

            # specify array parameters
            if {'Hook-Wire', 'paired'} == set(array_key.values()):
                
                # shank grid and geometries
                shank_spacing = (0, 60e-6, 0)
                shank_grid = np.array([
                    dict(
                        shank_dims = (0, 0, 0),
                        shank_tip_length = 0,
                        electrode_grid_shape = (1, 1),
                        electrode_grid_spacing = (0, 0),
                        enumerate_grid_from_bottom = True,
                        electrode_geometry = {'electrode_base_z_length': 123e-3, 'electrode_tip_z_length': 2e-3}
                    ),
                    dict(
                        shank_dims = (0, 0, 0),
                        shank_tip_length = 0,
                        electrode_grid_shape = (1, 1),
                        electrode_grid_spacing = (0, 0),
                        enumerate_grid_from_bottom = True,
                        electrode_geometry = {'electrode_base_z_length': 120e-3, 'electrode_tip_z_length': 5e-3}
                    )
                ]).reshape((1, 2, 1))

            elif {'Hook-Wire', 'clipped'} == set(array_key.values()):
                
                # shank grid and geometries
                shank_spacing = (0, 60e-6, 0)
                shank_grid = np.array([
                    dict(
                        shank_dims = (0, 0, 0),
                        shank_tip_length = 0,
                        electrode_grid_shape = (1, 1),
                        electrode_grid_spacing = (0, 0),
                        enumerate_grid_from_bottom = True,
                        electrode_geometry = {'electrode_base_z_length': 123e-3, 'electrode_tip_z_length': 1e-3}
                    ),
                    dict(
                        shank_dims = (0, 0, 0),
                        shank_tip_length = 0,
                        electrode_grid_shape = (1, 1),
                        electrode_grid_spacing = (0, 0),
                        enumerate_grid_from_bottom = True,
                        electrode_geometry = {'electrode_base_z_length': 120e-3, 'electrode_tip_z_length': 4e-3}
                    )
                ]).reshape((1, 2, 1))

            elif {'Hook-Wire', 'quad'} == set(array_key.values()):
                
                # shank grid and geometries
                shank_spacing = (60e-6, 60e-6, 0)
                shank_grid = np.array([
                    [
                        dict(
                            shank_dims = (0, 0, 0),
                            shank_tip_length = 0,
                            electrode_grid_shape = (1, 1),
                            electrode_grid_spacing = (0, 0),
                            enumerate_grid_from_bottom = True,
                            electrode_geometry = {'electrode_base_z_length': 124e-3, 'electrode_tip_z_length': 1e-3}
                        ),
                        dict(
                            shank_dims = (0, 0, 0),
                            shank_tip_length = 0,
                            electrode_grid_shape = (1, 1),
                            electrode_grid_spacing = (0, 0),
                            enumerate_grid_from_bottom = True,
                            electrode_geometry = {'electrode_base_z_length': 121.75e-3, 'electrode_tip_z_length': 3.25e-3}
                        )
                    ],
                    [
                        dict(
                            shank_dims = (0, 0, 0),
                            shank_tip_length = 0,
                            electrode_grid_shape = (1, 1),
                            electrode_grid_spacing = (0, 0),
                            enumerate_grid_from_bottom = True,
                            electrode_geometry = {'electrode_base_z_length': 117e-3, 'electrode_tip_z_length': 8e-3}
                        ),
                        dict(
                            shank_dims = (0, 0, 0),
                            shank_tip_length = 0,
                            electrode_grid_shape = (1, 1),
                            electrode_grid_spacing = (0, 0),
                            enumerate_grid_from_bottom = True,
                            electrode_geometry = {'electrode_base_z_length': 119.75e-3, 'electrode_tip_z_length': 5.25e-3}
                        )
                    ]
                ]).reshape((2, 2, 1))

            elif {'Neuropixels', 'nhp demo'} == set(array_key.values()):

                # electrode x-y coordinates
                x_coords = 1e-6 * np.repeat(np.array([[-6, 26, -26, 6]]), 32, axis=0).reshape(128,1)
                y_coords = 1e-6 * (350 + (np.array([[6, 6, 37, 37]]) + np.reshape(62 * np.arange(32), (32,1))).reshape(128,1))

                # shank grid and geometries
                shank_spacing = (0, 0, 0)
                shank_grid = np.array([
                    dict(
                        shank_dims = (120e-6, 45e-3, 120e-6),
                        shank_tip_length = 350e-6,
                        electrode_grid_coords = np.hstack((x_coords, y_coords)),
                        electrode_geometry = {'electrode_base_x_length': 12e-6}
                    )
                ]).reshape((1, 1, 1))

            elif {'S-Probe', '32 chan'} == set(array_key.values()):

                # shank grid and geometries
                shank_spacing = (0, 0, 0)
                shank_grid = np.array([
                    dict(
                        shank_dims = (300e-6, 100e-3, 300e-6),
                        shank_tip_length = 700e-6,
                        electrode_grid_shape = (1, 32),
                        electrode_grid_spacing = (0, 100e-6),
                        enumerate_grid_from_bottom = False,
                        electrode_geometry = {'electrode_base_x_length': 15e-6}
                    )
                ]).reshape((1, 1, 1))

            elif {'V-Probe', '24 chan'} == set(array_key.values()):

                # shank grid and geometries
                shank_spacing = (0, 0, 0)
                shank_grid = np.array([
                    dict(
                        shank_dims = (300e-6, 100e-3, 300e-6),
                        shank_tip_length = 300e-6,
                        electrode_grid_shape = (1, 24),
                        electrode_grid_spacing = (0, 100e-6),
                        enumerate_grid_from_bottom = False,
                        electrode_geometry = {'electrode_base_x_length': 15e-6}
                    )
                ]).reshape((1, 1, 1))

            elif {'Utah', '96 chan'} == set(array_key.values()):

                # shank grid and geometries
                shank_spacing = (400e-6, 400e-6, 0)
                shank_grid = np.tile(np.array([
                    dict(
                        shank_dims = (0, 0, 0),
                        shank_tip_length = 0,
                        electrode_grid_shape = (1, 1),
                        electrode_grid_spacing = (0, 0),
                        enumerate_grid_from_bottom = True,
                        electrode_geometry = {'electrode_tip_z_length': 1.5e-3}
                    )
                ]), (10, 10, 1))

            else:
                print('Key {} unrecognized'.format(array_key))
                shank_grid = np.array([])

            # build electrode array
            for shank_idx, (shank_coords, shank) \
                in enumerate(zip(np.ndindex(shank_grid.shape), shank_grid.flatten())):

                shank_key = dict(
                    **array_key,
                    shank_idx = shank_idx,
                    shank_x = Decimal(shank_spacing[0] * shank_coords[0]).quantize(Decimal('1e-9')),
                    shank_y = Decimal(shank_spacing[1] * shank_coords[1]).quantize(Decimal('1e-9')),
                    shank_z = Decimal(shank_spacing[2] * shank_coords[2]).quantize(Decimal('1e-9')),
                    shank_x_length = Decimal(shank['shank_dims'][0]).quantize(Decimal('1e-9')),
                    shank_y_length = Decimal(shank['shank_dims'][1]).quantize(Decimal('1e-9')),
                    shank_z_length = Decimal(shank['shank_dims'][2]).quantize(Decimal('1e-9')),
                    shank_tip_length = Decimal(shank['shank_tip_length']).quantize(Decimal('1e-9'))
                )

                self.Shank.insert1(shank_key)
                
                elec_geom_key = (ElectrodeGeometry & shank['electrode_geometry']).fetch1('KEY')

                if 'electrode_grid_coords' in shank.keys():

                    elec_keys = []
                    for elec_idx, elec_coords in enumerate(shank['electrode_grid_coords']):
                        
                        elec_keys.append(dict(
                            **array_key,
                            shank_idx = shank_idx,
                            electrode_idx = elec_idx,
                            electrode_x = Decimal(elec_coords[0]).quantize(Decimal('1e-9')),
                            electrode_y = Decimal(elec_coords[1]).quantize(Decimal('1e-9')),
                            **elec_geom_key
                        ))

                else:
                    # electrode grid midline (shank tip position)
                    electrode_grid_x_center = (shank['electrode_grid_spacing'][0] * (shank['electrode_grid_shape'][0] - 1))/2
                    electrode_grid_x_center = Decimal(electrode_grid_x_center).quantize(Decimal('1e-9'))

                    elec_keys = []
                    for elec_idx, elec_coords in enumerate(np.ndindex(shank['electrode_grid_shape'])):

                        # electrode x-y coordinates
                        electrode_x = shank['electrode_grid_spacing'][0] * elec_coords[0]
                        electrode_y = shank['electrode_grid_spacing'][1] * \
                            (elec_coords[1] if shank['enumerate_grid_from_bottom'] else shank['electrode_grid_shape'][1] - 1 - elec_coords[1])

                        elec_keys.append(dict(
                            **array_key,
                            shank_idx = shank_idx,
                            electrode_idx = elec_idx,
                            electrode_x = Decimal(electrode_x).quantize(Decimal('1e-9')) - electrode_grid_x_center,
                            electrode_y = Decimal(electrode_y).quantize(Decimal('1e-9')) + shank_key['shank_tip_length'],
                            **elec_geom_key
                        ))

                self.Electrode.insert(elec_keys)
        

@schema
class Hardware(dj.Lookup):
    definition = """
    hardware:                       varchar(32)  # hardware name
    ---
    -> EquipmentCategory
    hardware_model:                 varchar(255) # hardware model name
    hardware_manufacturer:          varchar(255) # hardware manufacturer
    hardware_manufacturer_location: varchar(255) # hardware manufacturer location
    hardware_manual_path = '':      varchar(255) # hardware manual file path
    """

    class Parameter(dj.Part):
        definition = """
        -> master
        -> EquipmentParameter
        ---
        equipment_parameter_value: float
        """

    contents = [
        #hardware name   |equipment category        |hardware model                         |hardware manufacturer         |hardware manufacturer location  |hardware manual path
        ['Speedgoat',     'task controller',         'Performance real-time target machine', 'Speedgoat GmbH',              'Liebefeld, Switzerland',        ''],
        ['Cerebus',       'neural signal processor', 'LB 0028',                              'Blackrock Microsystems',      'Salt Lake City, UT',            '/srv/locker/churchland/General/equipment-manuals/CerebusNSP.pdf'],
        ['CereStim',      'neural stimulator',       'LB 0314',                              'Blackrock Microsystems',      'Salt Lake City, UT',            '/srv/locker/churchland/General/equipment-manuals/CerestimR96.pdf'],
        ['StimPulse',     'neural stimulator',       '55-60-0',                              'FHC, Inc',                    'Bowdoin, ME',                   '/srv/locker/churchland/General/equipment-manuals/StimPulse.pdf'],
        ['Polaris',       'motion tracker',          'Spectra',                              'Northern Digital',            'Waterloo, Ontario, Canada',     '/srv/locker/churchland/General/equipment-manuals/Polaris.pdf'],
        ['5lb Load Cell', 'load cell',               'LRM200',                               'FUTEK',                       'Irvine, CA',                    '/srv/locker/churchland/General/equipment-manuals/LRM200_5lb.pdf'],
        ['DAM8',          'bioamplifier',            'ISO-DAM8A',                            'World Precision Instruments', 'Sarasota, FL',                  '/srv/locker/churchland/General/equipment-manuals/ISODAM8A.pdf'],
        ['CILUX chamber', 'chamber',                 '6-IAM-J0',                             'Crist Instrument Co Inc',     'Hagerstown, MD',                '']
    ]


@schema
class Software(dj.Lookup):
    definition = """
    software:                       varchar(32)  # software name
    software_version:               varchar(32)  # software release version
    ---
    -> EquipmentCategory
    software_manufacturer:          varchar(255) # software manufacturer
    software_manufacturer_location: varchar(255) # software manufacturer
    software_manual_path = '':      varchar(255) # software manual file path
    """

    class Parameter(dj.Part):
        definition = """
        -> master
        -> EquipmentParameter
        ---
        equipment_parameter_value: float
        """

    contents = [
        #software name  |software version |equipment category |software manufacturer |software manufacturer location |software manufacturer location  |software manual path
        ['Simulink',     '',               'task controller',  'MathWorks',           'Natick, MA',                   ''],
        ['Plexon OFS',   '4.5.0',          'spike sorter',     'Plexon',              'Dallas, TX',                   ''],
        ['Kilosort',     '2.0',            'spike sorter',     'Cortexlab',           'UCL',                          ''],
        ['Unity 3D',     '',               'graphics',         'Unity Technologies',  'San Francisco, CA',            ''],
        ['Psychtoolbox', '3.0',            'graphics',         'open source',         '',                             '']
    ]


# =======
# LEVEL 2
# =======

@schema
class ElectrodeArray(dj.Lookup):
    definition = """
    -> ElectrodeArrayModel
    electrode_array_id:          int unsigned # electrode array ID number
    ---
    electrode_array_serial = '': varchar(255) # electrode array serial number
    """


# =======
# LEVEL 3
# =======

@schema
class ElectrodeArrayConfig(dj.Lookup):
    definition = """
    # Mapping of electrode array electrodes to channels on a data array
    -> ElectrodeArray
    electrode_array_config_id: int unsigned     # electrode array configuration ID number
    ---
    -> lab.User                                 # user who made the configuration
    electrode_array_config_date: date           # date config file created
    electrode_array_config_notes: varchar(4095) # notes about the config file
    """

    class Channel(dj.Part):
        definition = """
        # Channel on recording file
        -> master
        ephys_channel_idx: int unsigned # channel index on ephys recording array
        """

    class Electrode(dj.Part):
        definition = """
        # Electrode on electrode array (one or more per channel for monopolar or differential configurations)
        -> master.Channel
        -> ElectrodeArrayModel.Electrode
        """

    @classmethod
    def ezinsert(
        self, 
        electrode_array: Tuple[str,str,int],
        user_uni: str, 
        channel_order: list, 
        config_date: str,
        config_notes: str=''
    ) -> None:
        """Easy insert new config file."""

        # match electrode array
        _, array_key = datajointutils.match_fuzzy_key(ElectrodeArray, electrode_array)

        # append next available config ID to array key
        new_config_id = datajointutils.next_unique_int(ElectrodeArrayConfig, 'electrode_array_config_id', array_key)
        config_key = dict(array_key, electrode_array_config_id=new_config_id)

        # make channel keys using input ordering
        channel_keys = [dict(config_key, ephys_channel_idx=chan) for chan in channel_order]

        # fetch model array electrode keys
        electrode_keys = (ElectrodeArrayModel.Electrode & config_key).fetch('KEY')

        # update electrode keys with channel information
        electrode_keys = [dict(chan_key, **elec_key) for chan_key, elec_key in zip(channel_keys, electrode_keys)]

        # insert config key
        self.insert1(dict(
            **config_key,
            user_uni=user_uni,
            electrode_array_config_date=config_date,
            electrode_array_config_notes=config_notes
        ))

        # insert channel keys
        self.Channel.insert(channel_keys)

        # insert electrode keys
        self.Electrode.insert(electrode_keys)