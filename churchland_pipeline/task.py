"""This module defines tables in the schema churchland_common_task"""

import datajoint as dj

schema = dj.schema('churchland_common_task')

@schema
class Task(dj.Lookup):
    definition = """
    task                 : varchar(32)
    ---
    task_description=""  : varchar(512)
    """
    contents = [
        ['pacman', '']
    ]

@schema
class ParameterCategory(dj.Lookup):
    definition = """
    parameter_category   : varchar(16)
    """
    contents = zip(['stim', 'target'])

@schema
class Parameter(dj.Lookup):
    definition = """
    parameter            : varchar(32)
    ---
    -> ParameterCategory
    parameter_description="" : varchar(255)                 # info such as the unit
    """

@schema
class TaskParameterSet(dj.Lookup):
    definition = """
    -> Task
    set_id=1             : int                          # parameter set id
    """

    class Parameter(dj.Part):
        definition = """
        -> master
        -> Parameter
        ---
        parameter_value      : blob
        """
