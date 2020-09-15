import os
import datajoint as dj

if os.environ.get('MODE') == 'production':
    dj.config['database.prefix'] = ''
else: # sandbox
    dj.config['database.prefix'] = os.environ.get('DJ_USER') + '_'