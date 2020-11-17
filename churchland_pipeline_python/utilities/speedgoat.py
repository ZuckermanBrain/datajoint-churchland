"""
This package defines modules for parsing data from speedgoat
"""

import re
import numpy as np
from itertools import compress

num_clock_bytes = 8
num_len_bytes = 2

def read_task_states(file_path):
    """Reads task states from .summary files

    Args:
        file_path ([type]): [description]

    Returns:
        [type]: [description]
    """
    
    # read summary text from file
    fid = open(file_path,'r')
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
    
def read_trial_params(file_path):
    """Reads trial parameters from .params files

    Args:
        file_path ([type]): [description]

    Returns:
        [type]: [description]
    """

    assert file_path.endswith('.params'), 'Unrecognized Speedgoat parameters file'

    # read trial number
    trial_num = re.search(r'beh_(\d*)',file_path).group(1)

    # read params from file
    with open(file_path,'r') as f:
        data = np.fromfile(file=f, dtype=np.uint8)

    if len(data) == 0:
        print('Trial {} excluded due to missing parameters'.format(trial_num))
        return None

    # read parameter keys and values from string
    paramStr = ';' + ''.join([chr(x) for x in data[num_clock_bytes:]])
    keys = re.findall(';(.*?):=',paramStr)
    vals = re.findall(':=(.*?);',paramStr)

    # matrix string pattern
    matstr = re.compile(r'(-?)(\[)(.*)(\])')

    # evaluate strings as numeric
    vals = [eval(matstr.search(x).group(1) + matstr.search(x).group(3)) for x in vals]

    # create parameter dictionary
    params = dict(zip(keys,vals))

    # read parameter type as character
    params['type'] = ''.join([chr(int(x)) for x in params['type']])
    
    return params

def read_trial_data(file_path, success_state, sample_rate):
    """Reads trial data from .data files

    Args:
        file_path ([type]): [description]
        success_state ([type]): [description]
        sample_rate ([type]): [description]

    Returns:
        [type]: [description]
    """

    assert file_path.endswith('.data'), 'Unrecognized Speedgoat data file'

    # read trial number
    trial_num = re.search(r'beh_(\d*)',file_path).group(1)
    
    # read data from file
    with open(file_path,'r') as f:
        data = np.fromfile(file=f, dtype=np.uint8)

    # reshape data stream
    nBytesPerTrial = int(num_clock_bytes + num_len_bytes + np.uint16(data[num_clock_bytes : num_clock_bytes+1]))
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
    
    idx = int(num_clock_bytes + num_len_bytes)
    NUM_CODE_BYTES = 3

    # simulation time
    SgTrial['simulation_time'] = data[:num_clock_bytes,:].flatten('F').view(np.double)

    # check for dropped packets
    if any([(x>int(0.5*sample_rate)) and x<int(1.5*sample_rate) for x in np.diff(SgTrial['simulation_time'])]):
        print('Trial {} excluded due to dropped packets'.format(trial_num))
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
    
    if lastState < success_state:
        print('Trial {} was incomplete and excluded'.format(trial_num))
        return None

    else:
        if lastState == success_state:
            SgTrial['successful_trial'] = 1
        else:
            SgTrial['successful_trial'] = 0

        # remove undecoded keys
        SgTrial = {k: v for k,v in zip(SgTrial.keys(), SgTrial.values()) if not isinstance(v,str)}
                    
        return SgTrial

    