"""Equipment schema.

This module contains class definitions for equipment.

Coordinate system: x (left/right, onscreen); y (up/down, onscreen); z (into screen)
"""

import datajoint as dj
import numpy as np
import re
from matplotlib import pyplot as plt, patches as patches
from mpl_toolkits.mplot3d import Axes3D, art3d

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
class ElectrodeGeometry(dj.Lookup):
    definition = """
    electrode_geometry_id: smallint unsigned # unique ID
    ---
    electrode_base_x_length:              float                           # (m) length of base along x-axis
    electrode_base_y_length:              float                           # (m) length of base along y-axis
    electrode_base_z_length   = 0:        float                           # (m) length of base along z-axis
    electrode_base_shape      = 'cuboid': enum('cuboid','cylinder')       # base shape
    electrode_base_insulation = 0:        float                           # (m) insulation coverage, starting from base top
    electrode_base_rotation   = 0:        float                           # (multiples of 2*pi) base rotation in x-y plane
    electrode_tip_z_length    = 0:        float                           # (m) length of tip along z-axis
    electrode_tip_profile     = 'linear': enum('linear','curved','sharp') # tip profile
    electrode_tip_insulation  = 0:        float                           # (m) insulation coverage, starting from tip bottom
    """

    contents = [
        #id  |base-x   |base-y   |base-z   |base shape |base ins. |base rot. |tip-z   |tip prof. |tip ins.
        [0,   12e-6,    12e-6,    0,        'cuboid',   0,         0,         0,       'linear',  0],        # flat square (e.g., Neuropixels)
        [1,   15e-6,    15e-6,    0,        'cylinder', 0,         0,         0,       'linear',  0],        # flat circle (e.g., S-Probes)
        [2,   100e-6,   100e-6,   0,        'cylinder', 0,         0,         1.5e-3,  'sharp',   0],        # cone (e.g., Utah array)
        [3,   100e-6,   100e-6,   139.5e-3, 'cylinder', 129.5e-3,  0,         0.5e-3,  'sharp',   0.4e-3],   # sharp cylinder w/ insulation (e.g., FHC sharp electrode)
        [4,   50e-6,    50e-6,    123e-3,   'cuboid',   0,         0,         2e-3,    'linear',  0],        # blunt cylinder w/ insulation (e.g., Natus hook-wire)
        [5,   50e-6,    50e-6,    120e-3,   'cuboid',   0,         0,         5e-3,    'linear',  3e-3],     # blunt cylinder w/ insulation (e.g., Natus hook-wire)
    ]

    def plot(self, center_coords, resolution=100):

        assert len(self) == 1, 'Specify one entry for plotting'

        # fetch electrode parameters
        params = self.fetch1()

        # ---------
        # PLOT BASE
        # ---------

        # base axes lengths
        base_axes_lengths = np.array([v for k,v in params.items() if re.search(r'base_\w_length',k) is not None])

        fig = plt.figure()

        # plot 2D
        if params['electrode_base_z_length'] == params['electrode_tip_z_length'] == 0:

            # base coordinates
            if params['electrode_base_shape'] == 'cuboid': # rectangle

                base_coords = (base_axes_lengths * np.array([
                    [ 0.5,-0.5,0],
                    [ 0.5, 0.5,0],
                    [-0.5, 0.5,0],
                    [-0.5,-0.5,0]])).T
                base_coords = np.concatenate((base_coords, base_coords[:,0,None]), axis=1)

            else: # ellipse

                theta = np.linspace(0, 2*np.pi, resolution)
                base_coords = np.concatenate((\
                    base_axes_lengths[0]/2 * np.cos(theta)[:,np.newaxis],\
                    base_axes_lengths[1]/2 * np.sin(theta)[:,np.newaxis],\
                    np.zeros((len(theta),1))), axis=1).T

            # plot base at each center
            for center in center_coords:
                plt.plot(center[0]+base_coords[0,:], center[1]+base_coords[1,:], 'k')

        else: # plot 3D

            ax = fig.gca(projection='3d')

            if params['electrode_base_shape'] == 'cuboid': # cuboid

                plot_shape = 'cuboid'

                # --------
                # PLOT TIP
                # --------

                if params['electrode_tip_profile'] == 'linear':

                    plot_shape = 'cuboid'

                elif params['electrode_tip_profile'] == 'curved':

                    plot_shape = 'pyramid with curved faces'

                else: # sharp

                    plot_shape = 'pyramid'
            

            else: # elliptic cylinder

                z = np.linspace(0, base_axes_lengths[2], resolution)
                theta = np.linspace(0, 2*np.pi, resolution)
                theta_grid, z_grid = np.meshgrid(theta, z)
                x_grid = base_axes_lengths[0]/2 * np.cos(theta_grid)
                y_grid = base_axes_lengths[1]/2 * np.sin(theta_grid)
                
                for center in center_coords:

                    # plot sides
                    ax.plot_surface(center[0]+x_grid, center[1]+y_grid, center[2]+z_grid)

                    # overlay insulation
                    
                    # plot bottom
                    bottom = patches.Ellipse((center[0],center[1]), base_axes_lengths[0], base_axes_lengths[1])
                    ax.add_patch(bottom)
                    art3d.pathpatch_2d_to_3d(bottom)

                # --------
                # PLOT TIP
                # --------

                if params['electrode_tip_profile'] == 'linear':

                    plot_shape = 'cylinder'

                elif params['electrode_tip_profile'] == 'curved':

                    plot_shape = 'dome'

                else: # sharp

                    plot_shape = 'cone'

@schema
class ElectrodeArrayModel(dj.Lookup):
    definition = """
    # Model of an electrode array
    electrode_array_model:      varchar(32)     # model name (e.g., Wire, Utah, Neuropixels)
    ---
    tissue_type: enum('brain','muscle') # tissue array used to record from
    invasive: bool
    base_vertices = null: longblob # (m; 3xN array) base hull vertices xyz-coordinates relative to origin
    """

    class Shank(dj.Part):
        definition = """
        -> master
        shank: int unsigned # shank index
        ---
        shank_vertices = null: longblob # (m; 3xN array) shank hull vertices xyz-coordinates relative to base
        """

    class Site(dj.Part):
        definition = """
        -> master.Shank
        site: int unsigned # site index
        ---
        site_x: float # (m) site center x-coordinate relative to shank
        site_y: float # (m) site center y-coordinate relative to shank
        site_z: float # (m) site center xz-coordinate relative to shank
        -> ElectrodeGeometry
        """

    #def summarize(self):

    # def build(design='planar array'):

    #     if design == 'planar array':

    #     elif design == 'fine wire':

    #     elif design == 'linear array':

# -------------------------------------------------------------------------------------------------------------------------------
# LEVEL 1
# -------------------------------------------------------------------------------------------------------------------------------

@schema
class ElectrodeArray(dj.Lookup):
    definition = """
    -> ElectrodeArrayModel
    electrode_array_id: int unsigned # unique ID number
    ---
    electrode_array_serial = null: varchar(255) # serial number
    """

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

# -------------------------------------------------------------------------------------------------------------------------------
# LEVEL 2
# -------------------------------------------------------------------------------------------------------------------------------

@schema
class ElectrodeArrayConfig(dj.Lookup):
    definition = """
    -> ElectrodeArray
    electrode_array_config_id: int unsigned # unique configuration ID
    """

    class Channel(dj.Part):
        definition = """
        -> master
        -> ElectrodeArrayModel.Site
        channel: int unsigned # channel index (i.e., on recording file)
        """