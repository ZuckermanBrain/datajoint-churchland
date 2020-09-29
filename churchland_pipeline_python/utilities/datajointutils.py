
"""DataJoint utilities.

This module contains utilities for DataJoint pipelines.

Todo:
    * populatedependents
"""

import datajoint as dj
import inspect
from itertools import chain
from functools import reduce

def getchildren(table, context=[]):
    """Gets children of a table.

    Args:
        table (datajoint.user_tables.OrderedClass): DataJoint table
        context (frame, optional): Frame used to evaluate table names. Defaults to [].

    Returns:
        children (list): Child tables
    """

    graph = table.connection.dependencies
    graph.load()
    child_names = list(graph.children(table.full_table_name).keys())
    children = gettables(child_names, context=context)
    return children

def getparents(table, context=[]):
    """Gets parents of a table.

    Args:
        table (datajoint.user_tables.OrderedClass): DataJoint table
        context (frame, optional): Frame used to evaluate table names. Defaults to [].

    Returns:
        parents (list): Parent tables
    """

    graph = table.connection.dependencies
    graph.load()
    parent_names = list(graph.parents(table.full_table_name).keys())
    parents = gettables(parent_names, context=context)
    return parents

def gettables(names, context=[]):
    """Gets tables from a list of names.

    Args:
        names (list): Strings of table names
        context (frame, optional): Frame used to evaluate table names. Defaults to [].

    Returns:
        tables (list): DataJoint tables
    """

    if context:
        tables = [eval(dj.table.lookup_class_name(x, context.f_globals), context.f_globals) for x in names]
    else:
        for frame in inspect.stack():
            try:
                eval(dj.table.lookup_class_name(names[0], frame[0].f_globals), frame[0].f_globals)
            except TypeError:
                pass
            else:
                tables = [eval(dj.table.lookup_class_name(x, frame[0].f_globals), frame[0].f_globals) for x in names]
    
    return tables

def nextkey(table, index=0):
    """Gets the next (unpopulated) key for a table.

    Args:
        table (datajoint.user_tables.OrderedClass): DataJoint table
        index (int, optional): Index of next key to fetch. Defaults to 0.

    Returns:
        key (dict): Primary key
    """

    keys = (table.key_source - table).proj().fetch(as_dict=True)
    if len(keys)>=1:
        return keys[index]
    else:
        return None

def joinparts(master, key={}, depth=1, context=[]):
    """Joins a master table with its parts.

    Args:
        master (datajoint.user_tables.OrderedClass): Master table
        key (dict, optional): Attributes used to restrict joined tables. Defaults to {}.
        depth (int, optional): Maximum depth of included part tables. Defaults to 1.
        context (list, optional): Frame used to find related tables. Defaults to [].

    Returns:
        joined_table (datajoint.user_tables.OrderedClass): Joined table
        part_tables (list): DataJoint tables included in the join
    """
    
    parts = dict.fromkeys(range(1+depth),[])
    for layer in range(1+depth):
        if layer == 0:
            parts[layer] = [master]

        else:
            parts[layer] = [child for parent in parts[layer-1] for child in getchildren(parent, context=context) if set(getparents(child, context=context))=={parent}]
            parts[layer] = [child for child in parts[layer] if (master * child) & key]

    part_tables = list(chain.from_iterable(parts.values()))
    joined_table = reduce(lambda a,b: a*b, part_tables) & key

    return joined_table, part_tables



