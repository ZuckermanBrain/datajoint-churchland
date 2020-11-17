import datajoint as dj
import os, sys

schema = dj.schema(dj.config.get('database.prefix') + 'churchland_common_reference')

# ==================
# RESEARCH COMPUTING
# ==================

@schema
class EngramTier(dj.Lookup):
    definition = """
    # Engram storage tiers
    engram_tier: varchar(32) # engram tier name
    """

    contents = [
        ['locker'],
        ['labshare'],
        ['staging']
    ]

    def get_remote_path(self):
        """Returns remote path (relative to U19 server) to a storage tier."""

        assert len(self)==1, 'Specify one tier'

        path_parts = ['', 'srv', self.fetch1('engram_tier'), 'churchland', '']

        return os.path.sep.join(path_parts) 


    def get_local_path(self):
        """Returns local path (inferred based on OS) to a storage tier."""

        assert len(self)==1, 'Specify one tier'

        path_parts = ['']

        engram_tier = self.fetch1('engram_tier')

        # check if we're on the U19 server
        if os.path.isdir('/srv'):
            path_parts.extend(['srv', engram_tier, 'churchland', ''])

        else:
            # identify local OS
            local_os = sys.platform
            local_os = local_os[:(min(3, len(local_os)))]

            # append OS default external volume name
            if local_os.lower() == 'lin':
                path_parts.append('mnt')

            elif local_os.lower() == 'win':
                path_parts.append('Y:') # will this always be true?

            elif local_os.lower() == 'dar':
                path_parts.append('Volumes')

            # append local storage tier name
            path_parts.extend(['Churchland-' + engram_tier, ''])

        return os.path.sep.join(path_parts)

    @classmethod
    def ensure_remote(self, path: str) -> str:
        """Ensures that a path to a storage tier is provided relative to the remote (U19) server."""

        # infer storage tier from file path
        engram_tier = {'engram_tier': tier for tier in self.fetch('engram_tier') if tier in path}

        # convert local path parts to remote
        path = path.replace((self & engram_tier).get_local_path(), (self & engram_tier).get_remote_path())

        return path

    @classmethod
    def ensure_local(self, path: str) -> str:
        """Ensures that a path to a storage tier is provided relative to the local filesystem."""

        # infer storage tier from file path
        engram_tier = {'engram_tier': tier for tier in self.fetch('engram_tier') if tier in path}

        # convert remote path parts to local
        path = path.replace((self & engram_tier).get_remote_path(), (self & engram_tier).get_local_path())

        return path


# ==========
# PHYSIOLOGY
# ==========

@schema
class BrainLandmark(dj.Lookup):
    definition = """
    brain_landmark_abbr: varchar(8)   # brain landmark abbreviation
    ---
    brain_landmark:      varchar(255) # brain landmark name
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
    brain_region_abbr: varchar(8)   # brain region abbreviation
    ---
    brain_region:      varchar(255) # brain region name
    """

    contents = [
        ['M1',  'primary motor cortex'],
        ['PMd', 'dorsal premotor cortex'],
        ['SMA', 'supplementary motor area']
    ]


@schema
class Muscle(dj.Lookup):
    definition = """
    muscle_abbr:      varchar(8)   # muscle abbreviation
    ---
    muscle:           varchar(255) # muscle name
    muscle_head = '': varchar(255) # muscle head
    """

    contents = [
        ['LonBic', 'biceps',           'long'],
        ['ShoBic', 'biceps',           'short'],
        ['AntDel', 'deltoid',          'anterior'],
        ['LatDel', 'deltoid',          'lateral'],
        ['PosDel', 'deltoid',          'posterior'],
        ['ClaPec', 'pectoralis major', 'clavicular'],
        ['StePec', 'pectoralis major', 'sternal'],
        ['SupTra', 'trapezius',        'superior'],
        ['LatTri', 'triceps',          'lateral'],
        ['LonTri', 'triceps',          'long'],
        ['MedTri', 'triceps',          'medial']
    ]