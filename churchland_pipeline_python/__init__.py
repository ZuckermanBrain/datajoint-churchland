import datajoint as dj
import os, glob
from os.path import dirname, basename, isfile, join
from dotenv import load_dotenv, find_dotenv

# load env file
load_dotenv(join(dirname(__file__), '..', '.env')) 

# write mode to database prefix
dj.config['database.prefix'] = (os.getenv("MODE") + '_' if os.getenv("MODE") is not None else '')

# update list of all modules
modules = glob.glob(join(dirname(__file__), "*.py"))
__all__ = [basename(f)[:-3] for f in modules if isfile(f) and not f.endswith('__init__.py') and not f.endswith('common.py')]