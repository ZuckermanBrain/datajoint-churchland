from os.path import dirname, basename, isfile, join
import glob
import datajoint as dj

# update list of all modules
modules = glob.glob(join(dirname(__file__), "*.py"))
__all__ = [basename(f)[:-3] for f in modules if isfile(f) and not f.endswith('__init__.py') and not f.endswith('common.py')]

dj.config['stores'] = {
    'churchlandlocker': {
        'protocol': 'file',
        'location': '/srv/locker/churchland',
        'stage': '/srv/locker/churchland'
    }
}