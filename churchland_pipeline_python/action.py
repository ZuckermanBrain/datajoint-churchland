import datajoint as dj
from . import lab, reference, equipment

schema = dj.schema('churchland_common_action')

@schema
class BurrHole(dj.Manual):
    definition = """
    -> lab.Monkey
    burr_hole_index: tinyint unsigned
    ---
    burr_hole_date: date
    burr_hole_x: decimal(5,3) # (mm)
    burr_hole_y: decimal(5,3) # (mm)
    burr_hole_notes: varchar(4095)
    """

    class User(dj.Part):
        definition = """
        # Personnel
        -> master
        -> lab.User
        """


@schema
class Mri(dj.Manual):
    definition = """
    -> lab.Monkey
    mri_date: date
    ---
    mri_notes: varchar(4095)
    """

    class Coords(dj.Part):
        definition = """
        # Coordinates
        -> master
        -> reference.BrainLandmark
        coords_id: smallint unsigned # ID number
        ---
        origin: bool        # coordinate(s) used to define the origin
        surface: bool       # superficial (True) or deep (False)
        mri_x: decimal(6,3) # medial/lateral (+/-) coordinates (mm)
        mri_y: decimal(6,3) # anterior/posterior (+/-) coordinates (mm)
        mri_z: decimal(6,3) # dorsal/ventral (+/-) coordinates (mm)
        hemisphere = null: enum('left', 'right')
        """

    class User(dj.Part):
        definition = """
        # MRI personnel
        -> master
        -> lab.User
        """
