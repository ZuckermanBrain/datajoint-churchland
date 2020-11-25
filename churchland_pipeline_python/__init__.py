import datajoint as dj
import os, re, glob
from os.path import dirname, basename, isfile, join
from dotenv import load_dotenv, find_dotenv

# load env file
load_dotenv(join(dirname(__file__), '..', '.env'))

# env dict
dj_env = {
    'DJ_HOST': 'database.host',
    'DJ_USER': 'database.user',
    'DJ_PASS': 'database.password'
}

# assign base config settings from env file
for env_name, config_name in dj_env.items():

    if os.getenv(env_name):

        dj.config[config_name] = os.getenv(env_name)

# assign database prefix if not on production installation
if os.getenv('MODE') and not re.match(r'datajoint\.u19motor\.zi\.columbia\.edu', dj.config['database.host']):

    dj.config['database.prefix'] = os.getenv('MODE')

else:
    dj.config['database.prefix'] = ''

# update list of all modules
modules = glob.glob(join(dirname(__file__), "*.py"))
__all__ = [basename(f)[:-3] for f in modules if isfile(f) and not f.endswith('__init__.py') and not f.endswith('common.py')]