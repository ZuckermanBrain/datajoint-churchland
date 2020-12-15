# load env file
import os, re, glob
from os.path import dirname, basename, isfile, join
from dotenv import load_dotenv, find_dotenv

try:
    load_dotenv(join(dirname(__file__), '..', '.env'))
except:
    pass
else:
    pass

# import datajoint
import datajoint as dj

# assign database prefix if not on production installation
if os.getenv('MODE') and not re.match(r'datajoint\.u19motor\.zi\.columbia\.edu', dj.config['database.host']):

    dj.config['database.prefix'] = os.getenv('MODE') + '_'

else:
    dj.config['database.prefix'] = ''

# update list of all modules
modules = glob.glob(join(dirname(__file__), "*.py"))
__all__ = [basename(f)[:-3] for f in modules if isfile(f) and not f.endswith('__init__.py') and not f.endswith('common.py')]