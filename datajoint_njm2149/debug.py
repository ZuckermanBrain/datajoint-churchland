# %%

import os, sys, pathlib
os.chdir('/home/njm2149/Documents/datajoint-churchland/churchland_pipeline/users/njm2149')
sys.path.insert(0, str(pathlib.Path(os.getcwd()).parents[2]))
sys.path.insert(0, str(pathlib.Path(os.getcwd()).parents[2]) + '/brPY/')
import datajoint as dj
from churchland_pipeline_python import action, acquisition, equipment, lab, processing, reference
from churchland_pipeline_python.utilities import speedgoat, datasync, datajoint_utils as dju
from churchland_pipeline_python.tasks.pacman import pacman_acquisition, pacman_processing
import re, inspect
import pandas as pd
import numpy as np
from datetime import datetime
from brpylib import NsxFile, brpylib_ver


# %%

dju.get_children(pacman_acquisition.Behavior.Condition)