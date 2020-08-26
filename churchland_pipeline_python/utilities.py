import datajoint as dj
import inspect

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