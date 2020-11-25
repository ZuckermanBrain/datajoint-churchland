
"""DataJoint utilities.

This module contains utilities for DataJoint pipelines.

Todo:
    * populatedependents
"""

import datajoint as dj
import inspect, re
import math, numpy as np
from itertools import chain
from functools import reduce
from types import FrameType
from typing import NewType, Tuple, List

DataJointTable = dj.user_tables.OrderedClass

def flatten_blobs(records: list, blob_names: list) -> list:
    """Flattens a list of dictionaries containing vector-valued attributes ("blobs").

    Separates each blob in the list of attributes into its own dictionary 
    with the scalar attributes duplicated. (Helpful for porting table entries to pandas.)

    Args:
        records (list): List of dictionaries.
        blob_names (list): Attribute names in each dictionary to be flattened.

    Returns:
        flat_records (list): List of dictionaries, flattened over all blob names.
    """
    
    # initialize output list
    flat_records = []

    for data in records:
        
        # extract tuple containing each set of blob values per dict
        key_value_set = [X for X in zip(*[data[key_name] for key_name in blob_names])]

        for key_values in key_value_set:

            # flatten dictionaries over blob values
            flat_records.append(dict(data, **{k:v for k,v in zip(blob_names, key_values)}))

    return flat_records


def get_context(table: DataJointTable) -> FrameType:
    """Gets table context."""

    # check stack for table context
    for frame in inspect.stack():
        try:
            eval(dj.table.lookup_class_name(table.full_table_name, frame[0].f_globals), frame[0].f_globals)
        except TypeError:
            pass
        else:
            context = frame[0]

    return context


def get_children(table: DataJointTable, context: FrameType=None) -> List[DataJointTable]:
    """Gets all child tables of a table."""

    # get table context
    if not context:
        context = get_context(table)

    # get child names
    child_names = list(table().children().keys())

    # get child tables
    children = [eval(dj.table.lookup_class_name(x, context.f_globals), context.f_globals) for x in child_names]

    return children


def get_parents(table: DataJointTable, context: FrameType=None) -> List[DataJointTable]:
    """Gets all parent tables of a table."""

    # get table context
    if not context:
        context = get_context(table)

    # get parent names
    parent_names = list(table().parents().keys())

    # get parent tables
    parents = [eval(dj.table.lookup_class_name(x, context.f_globals), context.f_globals) for x in parent_names]

    return parents


def get_parts(master_table: DataJointTable, context: FrameType=None) -> List[DataJointTable]:
    """Gets all part tables of a master table."""

    # get table context
    if not context:
        context = get_context(master_table)

    # database table name pattern
    db_name = re.compile('\.`(.*?)(_{2}|`)')

    # full master table name (without schema)
    master_name = db_name.search(master_table.full_table_name).group(1)

    # child table names
    child_names = list(master_table().children().keys())

    # part table names (children whose names are a subset of the master)
    part_names = [name for name in child_names
        if db_name.search(name) and master_name in db_name.search(name).group(1)]

    # get part tables
    part_tables = [eval(dj.table.lookup_class_name(x, context.f_globals), context.f_globals) for x in part_names]

    return part_tables


def insert_part(master: DataJointTable, part_name: str, **kwargs) -> None:
    """Inserts an entry to master-part tables, given the master table, the part table name,
    and a set of keyword arguments containing the part table attributes. Checks to ensure that
    the keyword arguments are all valid attributes of the part table. Assumes that entries in 
    the master table are uniquely identified by an ID number. Creates a new ID for each new entry
    so that every entry is uniquely identifiable by its ID across all part tables."""

    # read master table attributes
    master_table_attr = read_attributes(master)

    # validate master table format
    assert len(master_table_attr) == 1, 'Master table has more than one attribute'

    master_attr_name = next(iter(master_table_attr))
    assert '_id' in master_attr_name, 'Expected variable ID as master table attribute'

    try:
        # get part table
        part = getattr(master, part_name)

        # read part table attributes
        part_table_attr = read_attributes(part)

        # ensure keyword keys are members of secondary attributes list
        assert set(kwargs.keys()).issubset(set(part_table_attr.keys())), 'Unrecognized keyword argument(s)'

        # check if entry already exists in table
        if part():

            # append default values if missing
            for key,val in part_table_attr.items():
                if key not in kwargs.keys() and not math.isnan(val):
                    kwargs.update({key:val})

            # existing entries
            part_entity = part.fetch(as_dict=True)
            part_entity_attr = [{k:float(v) for k,v in entity.items() \
                if k != master_attr_name and v is not None} \
                for entity in part_entity]
            
            # cross reference
            assert not any([kwargs == entity_attr for entity_attr in part_entity_attr]), 'Duplicate entry!'

        # insert ID to master table
        master_key = {master_attr_name: next_unique_int(master, master_attr_name)}
        master.insert1(master_key)

        # insert entry to part table
        part.insert1(dict(**master_key, **kwargs))

    except AttributeError:
        print('Unrecognized part name: {}'.format(part_name))


def match_fuzzy_key(table: DataJointTable, fuzzy_key: tuple) -> (DataJointTable, dict):
    """Attemps to match a string or ordered sequence of strings with a primary key in the associated table."""

    # match fuzzy key with ordered primary keys in table
    key_match = {k:v for k,v in zip(table.primary_key, ([fuzzy_key] if isinstance(fuzzy_key,str) else fuzzy_key))}

    # fetch primary key(s)
    key = (table & key_match).fetch('KEY')
    if len(key) == 1:
        key = key[0]

    # return query
    query = table & key

    return query, key


def next_key(table: DataJointTable, index: int=0) -> dict:
    """Gets the next (unpopulated) key for a table."""

    keys = (table.key_source - table).fetch("KEY")
    if len(keys)>=1:
        return keys[index]
    else:
        return None


def next_unique_int(table: DataJointTable, attr: str, key: dict={}) -> int:
    """Gets the smallest unique integer attribute value. Can restrict inferrence of unique values with an optional key."""

    if not(table & key):
        min_val = 0
    else:
        all_val = table.fetch(attr)
        min_val = next(i for i in range(2+max(all_val)) if i not in all_val)

    return min_val


def join_parts(
    master: DataJointTable,
    key: dict={},
    depth: int=1,
    context: FrameType=None
    ) -> Tuple[DataJointTable, List[DataJointTable]]:
    """Joins a master table with its part tables.

    Args:
        master: Master table
        key: Attributes used to restrict joined tables
        depth: Maximum depth of included part tables
        context: Frame used to find related tables. If empty, uses the master table's context

    Returns:
        joined_table: Joined table
        part_tables: Tables included in the join
    """

    # get master context
    if not context:
        context = get_context(master)
    
    parts = dict.fromkeys(range(1+depth),[])
    for layer in range(1 + depth):
        if layer == 0:
            parts[layer] = [master]

        else:
            # get part tables in next layer for each table in previous layer
            parts[layer] = [part for parent in parts[layer - 1] for part in get_parts(parent, context=context)]

            # restrict part tables to those with attributes in the key
            parts[layer] = [part for part in parts[layer]
                if ((master * part) & key) and ((master * part) & key).attributes_in_restriction()]

    part_tables = list(chain.from_iterable(parts.values()))
    joined_table = reduce(lambda a,b: a*b, part_tables) & key

    return joined_table, part_tables


def read_attributes(table: DataJointTable) -> dict:
    """Reads the attribute names and default values for a table."""

    # parse table definition
    table_def = [s.lstrip() for s in table.definition.split('\n')]

    # replace null entries with nan
    table_def = [s.replace('null','nan') for s in table_def]

    # regular expression patterns for attribute names and default values
    attr_name = re.compile(r'\w+')
    attr_default = re.compile(r'\w+\s*=\s*(.*):')

    # construct dictionary of table attributes and default values
    table_attr = {attr_name.match(s).group(0) : (float(attr_default.match(s).group(1)) if attr_default.match(s) else np.nan) \
            for s in table_def if attr_name.match(s)}

    return table_attr
