import datajoint as dj
from ... import action, acquisition, equipment, lab, processing, reference
from ...tasks.pacman import pacman_acquisition, pacman_processing
import os, re, inspect
from datetime import datetime

# create virtual module (creates a schema with originally defined tables)
# first argument: package name, not relevant
# second argument: schema name, most important
# lab = dj.create_virtual_module('shan_costa_lab', 'shan_costa_lab') 
# lab.__name__
# lab.schema.drop()

def schema_drop_order():
    return [
        'churchland_shared_pacman_processing',
        'churchland_shared_pacman_acquisition',
        'churchland_common_processing',
        'churchland_common_acquisition',
        'churchland_common_action',
        'churchland_common_reference',
        'churchland_common_lab',
        'churchland_common_equipment'
    ]

def next_key(query,key_index=0):
    keys = (query.key_source - query).proj().fetch(as_dict=True)
    if len(keys)>=1:
        return keys[key_index]
    else:
        return None

def get_children(table):
    graph = table.connection.dependencies
    graph.load()
    children = [eval(dj.table.lookup_class_name(x, inspect.currentframe().f_globals)) for x in list(graph.children(table.full_table_name).keys())]
    return children

def get_parents(table):
    graph = table.connection.dependencies
    graph.load()
    parents = [eval(dj.table.lookup_class_name(x, inspect.currentframe().f_globals)) for x in list(graph.parents(table.full_table_name).keys())]
    return parents

def populate_dependents(table):

    children = get_children(table)

def fill_sessions():
    """
    Fill remaining session data
    """

    for session_key in acquisition.Session.fetch('KEY'):

        # add users
        acquisition.Session.User.insert1(dict(user='njm2149', **session_key), skip_duplicates=True)
        if session_key['session_date'] >= datetime.strptime('2019-11-01','%Y-%m-%d').date():
            acquisition.Session.User.insert1(dict(user='emt2177', **session_key), skip_duplicates=True)

        # add load cell
        acquisition.Session.Hardware.insert1(dict(
            **session_key,
            **(equipment.Hardware & {'hardware': '5lb Load Cell'}).fetch1('KEY')
            ))