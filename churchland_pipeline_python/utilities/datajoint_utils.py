import datajoint as dj
import inspect
from itertools import chain
from functools import reduce

def get_children(table):
    graph = table.connection.dependencies
    graph.load()
    names = list(graph.children(table.full_table_name).keys())
    for frame in inspect.stack():
        try:
            eval(dj.table.lookup_class_name(names[0], frame[0].f_globals), frame[0].f_globals)
        except TypeError:
            pass
        else:
            children = [eval(dj.table.lookup_class_name(x, frame[0].f_globals), frame[0].f_globals) for x in names]
    return children

def get_parents(table):
    graph = table.connection.dependencies
    graph.load()
    names = list(graph.parents(table.full_table_name).keys())
    for frame in inspect.stack():
        try:
            eval(dj.table.lookup_class_name(names[0], frame[0].f_globals), frame[0].f_globals)
        except TypeError:
            pass
        else:
            parents = [eval(dj.table.lookup_class_name(x, frame[0].f_globals), frame[0].f_globals) for x in names]
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



