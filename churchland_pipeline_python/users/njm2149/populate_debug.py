# %%

import os, sys, pathlib
os.chdir('/home/njm2149/Documents/datajoint-churchland/churchland_pipeline/users/njm2149')
sys.path.insert(0, str(pathlib.Path(os.getcwd()).parents[2]))
sys.path.insert(0, str(pathlib.Path(os.getcwd()).parents[2]) + '/brPY/')
import datajoint as dj
from churchland_pipeline import action, acquisition, equipment, lab, processing, reference
from churchland_pipeline.rigs.Jumanji import speedgoat
from churchland_pipeline.tasks.pacman import pacman_acquisition, pacman_processing
from churchland_pipeline.users.njm2149 import datajoint_utilities as dju
import re, inspect
import pandas as pd
import numpy as np
from datetime import datetime
from brpylib import NsxFile, brpylib_ver


# %%
key = dju.next_key(pacman_acquisition.Behavior, 0)

# insert entry to Behavior table
pacman_acquisition.Behavior.insert1(key, allow_direct_insert=True)

# local path to behavioral summary file and sample rate
beh_sum_path, fs = (acquisition.BehaviorRecording & key).fetch1('behavior_summary_file_path', 'behavior_sample_rate')
beh_sum_path = (reference.EngramPath & {'engram_tier': 'locker'}).ensurelocal(beh_sum_path)

# path to all behavior files
beh_path = os.path.sep.join(beh_sum_path.split(os.path.sep)[:-1] + [''])

# identify task controller
sess_equip = (acquisition.Session.Equipment & key) * equipment.Equipment
task_controller_hardware = (sess_equip & {'equipment_type': 'task controller hardware'}).fetch1('equipment_name')

if task_controller_hardware == 'Speedgoat':

    # load summary file
    summary = speedgoat.readtaskstates(beh_sum_path)

    # update task states
    pacman_acquisition.TaskState.insert(summary, skip_duplicates=True)

    # parameter and data files`
    beh_files = os.listdir(beh_path)
    param_files = list(filter(lambda f: f.endswith('.params'), beh_files))
    data_files = list(filter(lambda f: f.endswith('.data'), beh_files))

    # populate conditions from parameter files
    for f_param in param_files:

        # trial number
        trial = re.search(r'beh_(\d*)',f_param).group(1)

        # ensure matching data file exists
        if f_param.replace('params','data') in data_files:
            
            # read params file
            params = speedgoat.readtrialparams(beh_path + f_param)

            # convert params to condition keys
            force_key, stim_key, targ_key, targ_type_key, cond_rel, targ_rel = pacman_acquisition.ConditionParams.params2keys(params)
            
            # insert new condition if none exists
            if not(cond_rel & force_key & stim_key & targ_key & targ_type_key):

                # insert condition table
                if not(pacman_acquisition.ConditionParams()):
                    new_cond_id = 0
                else:
                    cond_id = pacman_acquisition.ConditionParams.fetch('condition_id')
                    new_cond_id = np.setdiff1d(np.arange(cond_id.max()+2), cond_id)[0]

                cond_key = {'condition_id': new_cond_id}
                pacman_acquisition.ConditionParams.insert1(cond_key, allow_direct_insert=True)

                # insert first-layer condition part tables
                for (p,k) in zip(['Force', 'Stim', 'Target'], [force_key, stim_key, targ_key]):

                    if not(k):
                        continue

                    part = getattr(pacman_acquisition.ConditionParams, p)
                    k_id = p.lower() + '_id'

                    if not(part & k):

                        if not(part()):
                            new_id = 0
                        else:
                            id = part.fetch(k_id)
                            new_id = np.setdiff1d(np.arange(id.max()+2), id)[0]

                        k[k_id] = new_id
                    else:
                        k[k_id] = np.unique((part & k).fetch(k_id))[0]

                    part.insert1(dict(ChainMap(cond_key, k)), allow_direct_insert=True)

                # insert second-layer condition target type part table
                targ_rel.insert1(dict(ChainMap(cond_key, {'target_id': targ_key['target_id']}, targ_type_key)), allow_direct_insert=True)

        else:
            print('Missing data file for trial {}'.format(trial))

    # populate trials from data files
    success_state = (pacman_acquisition.TaskState() & 'task_state_name="Success"').fetch1('task_state_id')

    for f_data in data_files:

        # trial number
        trial = int(re.search(r'beh_(\d*)',f_data).group(1))

        # find matching parameters file
        try:
            param_file = next(filter(lambda f: f_data.replace('data','params')==f, param_files))
        except StopIteration:
            print('Missing parameters file for trial {}'.format(trial))
        else:
            # convert params to condition keys
            params = speedgoat.readtrialparams(beh_path + param_file)
            force_key, stim_key, targ_key, targ_type_key, cond_rel, targ_rel = pacman_acquisition.ConditionParams.params2keys(params)

            # read data
            data = speedgoat.readtrialdata(beh_path + f_data, success_state, fs)

            # insert condition data
            cond_id = (cond_rel & force_key & stim_key & targ_key & targ_type_key).fetch1('condition_id')
            cond_key = dict(ChainMap(key, {'condition_id': cond_id}))
            pacman_acquisition.Behavior.Condition.insert1(cond_key, allow_direct_insert=True, skip_duplicates=True)

            # insert trial data
            trial_key = dict(ChainMap(cond_key, {'trial_number': trial}, {'save_tag': params['saveTag']}, data))
            pacman_acquisition.Behavior.Trial.insert1(trial_key, allow_direct_insert=True)

# %%
