"""
This package defines modules for parsing data from speedgoat
"""

import re
import numpy as np
from itertools import compress

# READ TASK STATES FROM SUMMARY
def readtaskstates(filePath):
    
    # read summary text from file
    fid = open(filePath,'r')
    summaryText = fid.read()
    fid.close()
    
    # convert summary text to dict
    keys = re.findall(';(.*?):=',summaryText)
    vals = re.findall(':=(.*?);',summaryText)
    
    # convert summary text to dict
    summaryText = ';' + summaryText
    keys = re.findall(';(.*?):=',summaryText)
    vals = re.findall(':=(.*?);',summaryText)
    
    # read set of task states as tuples
    prog = re.compile('TaskState(\d+)')
    taskStates = [(int(prog.search(k).group(1)), v[1:-1]) for k,v in zip(keys,vals) if prog.search(k) is not None]
    
    return taskStates
    

# READ TRIAL PARAMETERS
def readtrialparams(filePrefix, trialNo):
    
    NUM_CLOCK_BYTES = 8

    # full file
    file = filePrefix + '_{}'.format(str(trialNo).zfill(4))

    # read params from file
    fid = open(file + '.params', 'r')
    data = np.fromfile(file=fid, dtype=np.uint8)
    fid.close()

    # read parameter keys and values from string
    paramStr = ';' + ''.join([chr(x) for x in data[NUM_CLOCK_BYTES:]])
    keys = re.findall(';(.*?):=',paramStr)
    vals = re.findall(':=(.*?);',paramStr)

    # evaluate strings as numeric
    vals = [eval(re.search('(\[)(.*)(\])',x).group(2)) for x in vals]

    # create parameter dictionary
    params = dict(zip(keys,vals))

    # read parameter type as character
    params['type'] = ''.join([chr(int(x)) for x in params['type']])
    
    return params

# READ TRIAL DATA
def readtrialdata(filePrefix, trialNo):
    
    NUM_CLOCK_BYTES = 8
    NUM_LEN_BYTES = 2
    SAMPLE_RATE = 1e3
    SUCCESS_STATE = 100

    # full file
    file = filePrefix + '_{}'.format(str(trialNo).zfill(4))

    # read data from file
    fid = open(file + '.data', 'r')
    data = np.fromfile(file=fid, dtype=np.uint8)
    fid.close()

    # reshape data stream
    nBytesPerTrial = int(NUM_CLOCK_BYTES + NUM_LEN_BYTES + np.uint16(data[NUM_CLOCK_BYTES : NUM_CLOCK_BYTES+1]))
    data = data.reshape((nBytesPerTrial,-1), order='F')

    # Speedgoat to DataJoint trial data dictionary
    SgTrial = {
        'successful_trial': [],
        'simulation_time': [],
        'task_state': 'tst',
        'force_raw_online': 'for',
        'force_filt_online': 'fof',
        'stim': 'stm',
        'reward': 'rew',
        'photobox': 'frm'
    }
    
    idx = int(NUM_CLOCK_BYTES + NUM_LEN_BYTES)
    NUM_CODE_BYTES = 3

    # simulation time
    SgTrial['simulation_time'] = data[:NUM_CLOCK_BYTES,:].flatten('F').view(np.double)

    # check for dropped packets
    if any([(x>int(0.5*SAMPLE_RATE)) and x<int(1.5*SAMPLE_RATE) for x in np.diff(SgTrial['simulation_time'])]):
        print('Trial {} excluded due to dropped packets'.format(trialNo))
        return

    # read coded data
    while idx < nBytesPerTrial:

        # read data properties
        dName = ''.join([chr(x) for x in data[idx+np.r_[:NUM_CODE_BYTES], 0]]).lower()
        dType = chr(data[NUM_CODE_BYTES+idx,0])
        dLen = int(data[1+NUM_CODE_BYTES+idx+np.r_[:2],0].view(np.uint16))

        # read data values
        if dType == 'D':
            dBytes = 3+NUM_CODE_BYTES+idx+np.r_[:dLen*8]
            dVal = data[dBytes,:].flatten('F').view(np.double)
            idx = 1+dBytes[-1]

        elif dType == 'U':
            dBytes = 3+NUM_CODE_BYTES+idx
            dVal = data[dBytes,:].flatten('F')
            idx = 1+dBytes

        else:
            print('Unrecognized data type {}'.format(dType))
            idx += 1
            continue

        # Speedgoat to DataJoint dictionary key index
        inDict = [x==dName if type(x)==str else False for x in SgTrial.values()]
        if sum(inDict) == 1:

            kIdx = list(compress(range(len(inDict)), inDict))[0]

            # overwrite Speedgoat code with data values
            SgTrial[list(SgTrial.keys())[kIdx]] = dVal

    # trial result
    lastState = SgTrial['task_state'][-1]
    if lastState < SUCCESS_STATE:
        print('Trial {} was incomplete and excluded'.format(trialNo))
    else:
        if lastState == SUCCESS_STATE:
            SgTrial['successful_trial'] = 1
        else:
            SgTrial['successful_trial'] = 0
                
    return SgTrial