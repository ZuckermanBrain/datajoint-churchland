
"""DataJoint utilities.

This module contains utilities for DataJoint pipelines.

Todo:
    * populatedependents
"""

import datajoint as dj
import inspect
from itertools import chain
from functools import reduce

def getcontext(table):
    """Identifies table context

    Args:
        table (datajoint.user_tables.OrderedClass): DataJoint table

    Returns:
        context (frame): Table context
    """

    # inspect table members
    attributes = inspect.getmembers(table, lambda a:not(inspect.isroutine(a)))

    # full table name
    table_name = [a for a in attributes if a[0].startswith('full_table_name')][0][-1]

    # check stack for table context
    for frame in inspect.stack():
        try:
            eval(dj.table.lookup_class_name(table_name, frame[0].f_globals), frame[0].f_globals)
        except TypeError:
            pass
        else:
            context = frame[0]

    return context

def getchildren(table, context=[]):
    """Gets children of a table.

    Args:
        table (datajoint.user_tables.OrderedClass): DataJoint table
        context (frame, optional): Frame used to evaluate table names. Defaults to [].

    Returns:
        children (list): Child tables
    """

    # get table context
    if not context:
        context = getcontext(table)

    # get child names
    graph = table.connection.dependencies
    graph.load()
    child_names = list(graph.children(table.full_table_name).keys())

    # get child tables
    children = [eval(dj.table.lookup_class_name(x, context.f_globals), context.f_globals) for x in child_names]

    return children

def getparents(table, context=[]):
    """Gets parents of a table.

    Args:
        table (datajoint.user_tables.OrderedClass): DataJoint table
        context (frame, optional): Frame used to evaluate table names. Defaults to [].

    Returns:
        parents (list): Parent tables
    """

    # get table context
    if not context:
        context = getcontext(table)

    # get parent names
    graph = table.connection.dependencies
    graph.load()
    parent_names = list(graph.parents(table.full_table_name).keys())

    # get parent tables
    parents = [eval(dj.table.lookup_class_name(x, context.f_globals), context.f_globals) for x in parent_names]

    return parents

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

    # get master context
    if not context:
        context = getcontext(master)
    
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



