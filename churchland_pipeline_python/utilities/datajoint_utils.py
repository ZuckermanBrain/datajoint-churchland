import datajoint as dj
import inspect
from itertools import chain
from functools import reduce
from .. import lab, acquisition, equipment, reference
from ..tasks.pacman import pacman_acquisition, pacman_processing

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

def next_key(query,key_index=0):
    keys = (query.key_source - query).proj().fetch(as_dict=True)
    if len(keys)>=1:
        return keys[key_index]
    else:
        return None

def joinparts(table, key={}, depth=1):
    
    parts = dict.fromkeys(range(1+depth),[])
    for layer in range(1+depth):
        if layer == 0:
            parts[layer] = [table]

        else:
            parts[layer] = [child for parent in parts[layer-1] for child in get_children(parent) if set(get_parents(child))=={parent}]
            parts[layer] = [child for child in parts[layer] if (table * child) & key]

    part_tables = list(chain.from_iterable(parts.values()))
    joined_table = reduce(lambda a,b: a*b, part_tables) & key

    return joined_table, part_tables

def populate_dependents(table):

    children = get_children(table)



