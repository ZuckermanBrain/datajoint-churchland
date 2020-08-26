import datajoint as dj

dj.config['stores'] = {
    'churchlandlocker': {
        'protocol': 'file',
        'location': '/srv/locker/churchland',
        'stage': '/srv/locker/churchland'
    }
}