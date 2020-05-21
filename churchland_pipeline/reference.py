import datajoint as dj

schema = dj.schema('churchland_reference')

@schema
class BrainRegion(dj.Lookup):
    definition = """
    brain_abbrev : varchar(8) # brain region abbreviation
    ---
    brain_name : varchar(64) # brain region
    """
    
    contents = [
        ['M1','primary motor cortex'],
        ['PMd','dorsal premotor cortex']
    ]
    
@schema
class Muscle(dj.Lookup):
    definition = """
    muscle_abbrev : varchar(8) # muscle abbreviation
    ---
    muscle_name : varchar(64) # muscle name
    muscle_head = null : varchar(64) # muscle head
    """
    
    contents = [
        ['AntDel','deltoid','anterior'],
        ['LatDel','deltoid','lateral'],
        ['ClaPec','pectoralis major','clavicular'],
        ['StePec','pectoralis major','sternal'],
        ['LatTri','triceps','lateral'],
        ['LatMed','triceps','medial']
    ]
    
@schema
class Sulcus(dj.Lookup):
    definition = """
    sulcus_abbrev : varchar(8) # sulcus abbreviation
    ---
    sulcus_name : varchar(64) # sulcus name
    """
    
    contents = [
        ['LF','Longitudinal Fissure'],
        ['CS','Central Sulcus'],
        ['SPD','Superior Precentral Dimple'],
        ['SAS','Superior Arcuate Sulcus'],
        ['IAS','Inferior Arcuate Sulcus']
    ]