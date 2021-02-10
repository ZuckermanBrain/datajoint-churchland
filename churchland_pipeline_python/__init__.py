import os, re, glob
import datajoint as dj
from os.path import dirname, basename, isfile, join
from dotenv import dotenv_values, find_dotenv

dj_env = {
    'DJ_HOST': 'database.host',
    'DJ_USER': 'database.user',
    'DJ_PASS': 'database.password'
}

try:
    env_values = dotenv_values(find_dotenv())
except:
    env_values = {}

for env_name, config_name in dj_env.items():
    if env_name in env_values.keys():
        dj.config[config_name] = env_values[env_name]

running_production = re.match(r'datajoint\.u19motor\.zi\.columbia\.edu', dj.config['database.host'])
if 'MODE' in env_values.keys() and not running_production:
    dj.config['database.prefix'] = env_values['MODE'] + '_'
else:
    dj.config['database.prefix'] = ''

# update list of all modules
modules = glob.glob(join(dirname(__file__), "*.py"))
__all__ = [basename(f)[:-3] for f in modules \
    if isfile(f) and not f.endswith('__init__.py') and not f.endswith('common.py')]