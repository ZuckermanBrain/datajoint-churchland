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
    burr_hole_notes : varchar(4095)
    """

    class User(dj.Part):
        definition = """
        # Personnel
        -> master
        -> lab.User
        """

# microstim

@schema
class MRI(dj.Manual):
    definition = """
    -> lab.Monkey
    mri_date: date
    ---
    -> reference.Sulcus
    mri_x : decimal(6,3) # medial/lateral (+/-) coordinates [mm]
    mri_y : decimal(6,3) # dorsal/ventral (+/-) coordinates [mm]
    mri_z : decimal(6,3) # anterior/posterior (+/-) coordinates [mm]
    mri_notes : varchar(4095)
    """

# palpation
# surgery types? (implant, array, )


@schema
class Surgery(dj.Manual):
    definition = """
    -> lab.Monkey
    surgery_date: date
    ---
    surgery_notes : varchar(4095)
    """

    class Hardware(dj.Part):
        definition = """
        -> master
        -> equipment.Hardware
        """

    class User(dj.Part):
        definition = """
        # Personnel
        -> master
        -> lab.User
        """
