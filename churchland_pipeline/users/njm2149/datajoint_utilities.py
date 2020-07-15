import datajoint as dj
from ... import action, acquisition, equipment, lab, processing, reference
from ...tasks.pacman import pacman_acquisition, pacman_processing
import os, re, inspect
from collections import ChainMap
from datetime import datetime

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

    for sess_key in acquisition.Session.fetch('KEY'):

        # add users
        acquisition.Session.User.insert1((sess_key['session_date'], sess_key['monkey'], 'njm2149'), skip_duplicates=True)
        if sess_key['session_date'] >= datetime.strptime('2019-11-01','%Y-%m-%d').date():
            acquisition.Session.User.insert1((sess_key['session_date'], sess_key['monkey'], 'emt2177'), skip_duplicates=True)

        # add load cell
        equip_key = (equipment.Equipment & 'equipment_type="load cell"').fetch1('KEY')
        acquisition.Session.Equipment.insert1(dict(ChainMap(sess_key, equip_key)), skip_duplicates=True)