"""
Package for synchronizing data across acquisition systems
"""

import numpy as np
import warnings
from itertools import compress


def decodesyncsignal(sync_signal, fs, max_sample_err=2, max_time_step=0.2):

    # number of data samples
    num_samples = len(sync_signal)

    # denoised sync signal
    sync_signal = sync_signal > sync_signal.mean()

    # expected number of samples between sync signal edges based on timing code //TODO add more details about the timing code
    samples_per_ms = int(round(fs/1e3))
    expected_pulse_len = dict(
        low           =       samples_per_ms,
        high          =   2 * samples_per_ms,
        inter_block   =   6 * samples_per_ms,
        dropped_block = 106 * samples_per_ms
        )

    # indices of rising and falling edges in sync pulses
    edge_idx = list(compress(range(num_samples), np.insert(np.diff(sync_signal),0,False)))

    # samples between rising and falling edges
    pulse_len = np.diff(edge_idx)
    num_pulses = len(pulse_len)

    # remove partial leading and trailing blocks
    new_block = (pulse_len >= expected_pulse_len['inter_block'])
    first_block_edge_start = next(compress(range(num_pulses), new_block))
    last_block_edge_end = num_pulses-next(compress(range(num_pulses), np.flip(new_block)))
    edge_idx = edge_idx[1+first_block_edge_start:last_block_edge_end]

    # update record of pulse lengths
    pulse_len = np.diff(edge_idx)
    num_pulses = len(pulse_len)

    # map each unique pulse length to closest expected length
    nearest_expected_pulse_len = {unq_pulse_len: min(expected_pulse_len.values(), key=lambda x: abs(x-unq_pulse_len)) for unq_pulse_len in np.unique(pulse_len)}

    # find the first pulse in each sync block
    first_pulse = np.insert([nearest_expected_pulse_len[y] > expected_pulse_len['high'] for y in pulse_len],0,False)
    first_pulse = np.insert(list(compress(range(num_pulses), first_pulse)),0,0)

    # remove "first" pulses with insufficient data for a full time stamp
    first_pulse = first_pulse[first_pulse+63 < num_pulses]

    # extract timing code from sync blocks
    new_block_idx = [edge_idx[i] for i in first_pulse]
    sync_blocks = [dict(start=new_block_idx[i], code=pulse_len[first_pulse[i]+range(0,63,2)]) for i in range(len(new_block_idx))]

    # infer corrupted sync blocks by comparing code with expected pulse lengths
    expected_code_lengths = np.array([expected_pulse_len['low'], expected_pulse_len['high']]).reshape((2,1))

    for block in sync_blocks:

        # absolute difference between block code and expected code lengths
        code_error = np.min(abs(block['code'] - expected_code_lengths), axis=0)

        # initialize record of corrupted sync blocks if large errors in any code pulse
        block.update(corrupted=any(code_error > max_sample_err))

    # convert timing code to binary
    for block in sync_blocks:

        block.update(code=(
            np.round((block['code'] - expected_pulse_len['low'])/expected_pulse_len['low'])
            if not block['corrupted'] else None
        ))
    
    # decode sync blocks
    pow_2 = np.array([2**i for i in range(32)])

    [block.update(time=(sum(block['code'] * pow_2)/10 if not block['corrupted'] else np.nan)) \
        for block in sync_blocks];

    # indicate any blocks whose encoded time exceeds the recording duration as corrupted
    t_max = sync_blocks[0]['time'] + num_samples/fs

    [block.update(corrupted=block['time'] > t_max) for block in sync_blocks if not block['corrupted']];

    # indicate any blocks with large sequential time steps or time reversals as corrupted
    for idx, block in enumerate(sync_blocks, start=1):

        if not block['corrupted']:
            
            block.update(corrupted=(
                block['time'] > (sync_blocks[idx-1]['time'] + max_time_step) or 
                block['time'] < sync_blocks[idx-1]['time']
            ))

    # throw warning for high proportions of corrupted sync blocks
    p_corrupted = 100 * len([block for block in sync_blocks if block['corrupted']]) / len(sync_blocks)
    if p_corrupted > 10:
        warnings.warn('{:.2f}% corrupted sync blocks. Timing estimate may be unreliable.'.format(p_corrupted))

    # return uncorrupted sync blocks
    sync_blocks = [block for block in sync_blocks if not block['corrupted']]

    return sync_blocks


def ephystrialstart(fs_ephys, trial_time, sync_block_start, sync_block_time):

    # trial start time (Speedgoat clock)
    speedgoat_trial_start_time = [t[0] for t in trial_time]

    # bin edges between ephys sample indices
    sync_block_start_bins = np.concatenate((sync_block_start[:-1,np.newaxis], sync_block_start[1:,np.newaxis]), axis=1).mean(axis=1)
    sync_block_start_bins = np.append(np.insert(sync_block_start_bins,0,0), np.Inf)

    # bin edges between Speedgoat time stamp
    sync_block_time_bins = np.concatenate((sync_block_time[:-1,np.newaxis], sync_block_time[1:,np.newaxis]), axis=1).mean(axis=1)
    sync_block_time_bins = np.append(np.insert(sync_block_time_bins,0,0), np.Inf)

    # function to map ephys sample index to Speedgoat time base using a selected sync block
    samp2time = lambda xi,sync_idx: round(sync_block_time[sync_idx] + (xi-sync_block_start[sync_idx])/fs_ephys, 6)

    # preallocate array of trial start indices
    ephys_trial_start_idx = np.empty(len(speedgoat_trial_start_time))

    for i0,t0 in enumerate(speedgoat_trial_start_time):

        if t0 < sync_block_time[0] or t0 > sync_block_time[-1]:
            ephys_trial_start_idx[i0] = np.nan

        else:
            # find the sync block whose encoded time is nearest the trial start time
            nearest_block = np.digitize(t0, sync_block_time_bins) - 1

            # sample index range containing the nearest sync block
            idx_range = range(\
                np.floor(sync_block_start_bins[nearest_block]).astype(int), \
                1+np.ceil(sync_block_start_bins[-2]).astype(int))

            # nearest sample to the encoded trial start time
            ephys_trial_start_idx[i0] = next(i for i in idx_range if samp2time(i,nearest_block) >= t0)

    # temporal correction
    ephys_trial_start_idx -= round(0.1 * fs_ephys)

    return ephys_trial_start_idx