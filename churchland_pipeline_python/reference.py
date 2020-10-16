import datajoint as dj
import os, sys

schema = dj.schema('churchland_common_reference')

# Research Computing

@schema
class EngramPath(dj.Lookup):
    definition = """
    # Provides the local path to Engram whether working on the server or a local machine
    engram_tier: varchar(32)               # engram data tier name
    """

    contents = [
        ['locker'],
        ['labshare']
    ]

    def getglobalpath(self):

        assert len(self)==1, 'Request one path'
        path_parts = ['', 'srv', self.fetch1('engram_tier'), 'churchland', '']
        return os.path.sep.join(path_parts) 

    def getlocalpath(self):

        assert len(self)==1, 'Request one path'

        path_parts = ['']
        engram_tier = self.fetch1('engram_tier')

        # check if we're on the U19 server
        if os.path.isdir('/srv'):
            path_parts.extend(['srv', engram_tier, 'churchland', ''])

        else:
            local_os = sys.platform
            local_os = local_os[:(min(3, len(local_os)))]
            if local_os.lower() == 'lin':
                path_parts.append('mnt')

            elif local_os.lower() == 'win':
                path_parts.append('Y:') # will this always be true?

            elif local_os.lower() == 'dar':
                path_parts.append('Volumes')

            path_parts.extend(['Churchland-' + engram_tier, ''])

        return os.path.sep.join(path_parts)
    
    def ensureglobal(self, path):

        assert len(self)==1, 'Request one path'
        return path.replace(self.getlocalpath(), self.getglobalpath())

    def ensurelocal(self, path):

        assert len(self)==1, 'Request one path'
        return path.replace(self.getglobalpath(), self.getlocalpath())


# Physiology

@schema
class BrainLandmark(dj.Lookup):
    definition = """
    brain_landmark_abbrev:    varchar(8)                 # landmark abbreviation
    ---
    brain_landmark:           varchar(255)               # landmark full name
    """

    contents = [
        ['LF',  'Longitudinal Fissure'],
        ['CS',  'Central Sulcus'],
        ['SPD', 'Superior Precentral Dimple'],
        ['SAS', 'Superior Arcuate Sulcus'],
        ['IAS', 'Inferior Arcuate Sulcus']
    ]

@schema
class BrainRegion(dj.Lookup):
    definition = """
    brain_region_abbrev: varchar(8)   # brain region abbreviation
    ---
    brain_region:        varchar(255) # brain region full name
    """

    contents = [
        ['M1','primary motor cortex'],
        ['PMd','dorsal premotor cortex']
    ]

@schema
class Muscle(dj.Lookup):
    definition = """
    muscle_abbrev:    varchar(8)   # muscle abbreviation
    ---
    muscle:           varchar(255) # muscle name
    muscle_head = '': varchar(255) # muscle head
    """

    contents = [
        ['AntDel','deltoid','anterior'],
        ['LatDel','deltoid','lateral'],
        ['ClaPec','pectoralis major','clavicular'],
        ['StePec','pectoralis major','sternal'],
        ['LatTri','triceps','lateral'],
        ['LatMed','triceps','medial']
    ]