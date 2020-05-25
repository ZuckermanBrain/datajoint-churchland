import datajoint as dj

schema = dj.schema('churchland_lab')

@schema
class Monkey(dj.Lookup):
    definition = """
    monkey: varchar(32) # unique monkey name
    ---
    """

@schema
class Protocol(dj.Lookup):
    definition = """
    # IACUC protocol
    protocol: varchar(16)
    ---
    protocol_type: varchar(16)
    protocol_description='' : varchar(255)
    """

@schema
class User(dj.Lookup):
    definition = """
    user: varchar(32) # unique user identifier (CU uni)
    ---
    user_name: varchar(128) # first and last name
    """
