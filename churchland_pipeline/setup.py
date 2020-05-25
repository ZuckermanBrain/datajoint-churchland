import datajoint as dj

dj.config['database.host'] = 'localhost'
dj.config['database.user'] = 'ChurchlandLab_test'
dj.config['database.password'] = 'test1'


dj.config.save_local()
dj.config.save_global()
