import datajoint as dj
from . import lab, reference

schema = dj.schema('churchland_action')

@schema
class BurrHole(dj.Manual):
    definition = """
    burr_hole_date: date
    -> lab.Monkey
    ---
    -> lab.User
    """
    
# microstim

@schema
class MRI(dj.Manual):
    definition = """
    mri_date: date
    -> lab.Monkey
    ---
    -> reference.Sulcus
    x : decimal(6,3) # medial/lateral (+/-) coordinates [mm]
    y : decimal(6,3) # dorsal/ventral (+/-) coordinates [mm]
    z : decimal(6,3) # anterior/posterior (+/-) coordinates [mm]
    """
    
# palpation
    

@schema
class Surgery(dj.Manual):
    definition = """
    surgery_date: date
    -> lab.Monkey
    ---
    -> lab.User
    """
    