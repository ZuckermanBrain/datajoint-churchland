# Churchland Lab Pipeline

This repository contains files for developing and interacting with the Churchland Lab pipeline using DataJoint. DataJoint is a language-agnostic relational database management system for organizing, populating, computing, and querying data (see the [DataJoint documentation](https://docs.datajoint.io/) for more details). The data are hosted on the U19 server, which runs two separate installations of DataJoint: a _development_ installation, for prototyping new analysis pipelines and workflows, and a _production_ installation, for mature, well-tested pipelines (see the [U19 DataJoint documentation](https://confluence.columbia.edu/confluence/display/zmbbi/Datajoint) for more details). To get started, see the Wiki pages for [MATLAB](https://github.com/ZuckermanBrain/datajoint-churchland/wiki/Getting-Started-(MATLAB)) or [Python](https://github.com/ZuckermanBrain/datajoint-churchland/wiki/Getting-Started-(Python)).

## Staying updated

If you installed the pipeline as a 'contributor' (see the getting started guides, linked above), you can easily stay updated with new releases via git. For this, you will need to configure Zuckerman Brain as 'upstream' for your fork. Check this in the terminal by running
```console
$ git remote -v
```

If there is no upstream pointing to the Zuckerman Brain repository, then execute
```console
$ git remote add upstream https://github.com/ZuckermanBrain/datajoint-churchland
```
Then use `git pull upstream master` to pull the changes from the upstream repo into your local fork.

## Contributing code

If you feel happy with the changes you've made, you can add, commit and push them to your own branch. Then go to your fork on Github, click 'Pull requests', 'New pull request', 'compare across forks', and select your fork of `datajoint-churchland`. If there are no merge conflicts, you can click 'Create pull request', explain what changes/contributions you've made, and and submit it to the DataJoint team for approval.

## Pipeline schemas

### Base schemas

#### Equipment
![equipment erd](images/equipment_erd.png)

#### Lab
![equipment erd](images/lab_erd.png)

#### Reference
![equipment erd](images/reference_erd.png)

#### Action
![equipment erd](images/action_erd.png)

#### Acquisition
![acquisition erd](images/acquisition_erd.png)

#### Processing
![acquisition erd](images/processing_erd.png)

### Joined schemas

#### Acquisition+
![acquisition erd](images/acquisition_plus_erd.png)

#### Neural
![neural erd](images/neural_erd.png)

#### EMG
![emg erd](images/emg_erd.png)
