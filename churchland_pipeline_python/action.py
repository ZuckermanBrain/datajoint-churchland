import datajoint as dj
from . import lab, reference, equipment
import pandas as pd

schema = dj.schema('churchland_common_action')

# =======
# LEVEL 0
# =======

@schema
class Chamber(dj.Manual):
    definition = """
    # Neural recording chamber
    -> lab.Monkey
    chamber_id:   tinyint unsigned # chamber ID number
    ---
    chamber_date: date             # chamber implantation date
    chamber_x:    decimal(5,3)     # chamber center x-coordinate (+/-, lateral/medial) on brain (mm)
    chamber_y:    decimal(5,3)     # chamber center y-coordinate (+/-, anterior/posterior) on brain (mm)
    -> equipment.Hardware          # physical chamber and its geometry
    """

    class User(dj.Part):
        definition = """
        # Chamber implantation personnel
        -> master
        -> lab.User
        """


@schema
class Mri(dj.Manual):
    definition = """
    -> lab.Monkey
    -> lab.User                   # person who documented landmarks
    mri_date:       date          # MRI procedure date
    ---
    mri_notes = '': varchar(4095) # MRI notes
    """

    class Landmark(dj.Part):
        definition = """
        # MRI landmark coordinates
        -> master
        -> reference.BrainLandmark
        landmark_id:      tinyint unsigned                 # landmark ID number
        ---
        brain_hemisphere: enum('left', 'right', 'midline') # brain hemisphere or midline
        brain_surface:    bool                             # whether landmark is on the brain surface (True) or deep (i.e., in a sulcus)
        landmark_x:       decimal(6,3)                     # landmark x-coordinate (+/-, lateral/medial) (mm)
        landmark_y:       decimal(6,3)                     # landmark y-coordinate (+/-, anterior/posterior) (mm)
        landmark_z:       decimal(6,3)                     # landmark z-coordinate (+/-, dorsal/ventral) (mm)
        origin = 0:       bool                             # whether landmark should be used to define the origin
        """
        
    @classmethod
    def insert_from_file(self,
        file_path: str, 
        monkey: str, 
        user_uni: str, 
        mri_date: str, 
        mri_notes: str=''
    ) -> None:
        """Inserts MRI entries and landmarks by reading data from a csv file."""

        # add entry to master table
        master_key = dict(
            monkey=monkey,
            user_uni=user_uni,
            mri_date=mri_date,
        )

        self.insert1(dict(**master_key, mri_notes=mri_notes))

        # load file as data frame
        landmark_df = pd.read_csv(file_path)

        # convert data frame to list of keys
        landmark_keys = landmark_df.to_dict(orient='records')

        # append master key to landmark keys
        landmark_keys = [dict(**master_key,**k) for k in landmark_keys]

        # insert to part table
        self.Landmark.insert(landmark_keys)



# =======
# LEVEL 1
# =======

@schema
class BurrHole(dj.Manual):
    definition = """
    # Small access hole in chamber for neural probes
    -> lab.Monkey
    -> Chamber
    burr_hole_id:             smallint unsigned # burr hole ID number
    ---
    burr_hole_date:           date              # burr hole procedure date
    burr_hole_x:              decimal(5,3)      # burr hole center x-coordinate (+/-, lateral/medial) relative to chamber center (mm)
    burr_hole_y:              decimal(5,3)      # burr hole center y-coordinate (+/-, anterior/posterior) relative to chamber center (mm)
    burr_hole_diameter = 3.5: decimal(5,3)      # burr hole diameter (mm)
    burr_hole_notes = '':     varchar(4095)     # burr hole notes
    """

    class User(dj.Part):
        definition = """
        # Burr hole procedure personnel
        -> master
        -> lab.User
        """