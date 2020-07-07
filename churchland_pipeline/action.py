import datajoint as dj
from . import lab, reference

schema = dj.schema('churchland_action')

@schema
class BurrHole(dj.Manual):
    definition = """
    -> lab.Monkey
    burr_hole_inx: tinyint unsigned
    ---
    burr_hole_date: date
    burr_hole_x: decimal(5,3) # (mm)
    burr_hole_y: decimal(5,3) # (mm)
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
    # notes (?)
    """

# palpation


@schema
class Surgery(dj.Manual):
    definition = """
    -> lab.Monkey
    surgery_date: date
    ---
    -> lab.User
        # notes (?)
    """
