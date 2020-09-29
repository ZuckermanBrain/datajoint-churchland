# %%

import os, sys, pathlib
os.chdir('/home/njm2149/Documents/datajoint-churchland/datajoint_njm2149')
[sys.path.insert(0, str(pathlib.Path(os.getcwd()).parents[0]) + d) for d in ['', '/brPY']];
import datajoint as dj
from churchland_pipeline_python import action, acquisition, equipment, lab, processing, reference
from churchland_pipeline_python.utilities import speedgoat, datasync, datajoint_utils as dju
#from churchland_pipeline_python.common import *
from datajoint_pacman import pacman_acquisition, pacman_processing
images_path = '/home/njm2149/Documents/datajoint-churchland/images/'

import re, inspect
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from brpylib import NsxFile, brpylib_ver
from itertools import compress, chain
from functools import reduce
import warnings
import timeit

# %%