"""
This package defines modules for parsing data from speedgoat
"""

import os, re
import numpy as np
from collections import defaultdict
from itertools import compress

N_CLOCK_BYTES = 8
N_LEN_BYTES = 2
N_CODE_BYTES = 3


class SpeedgoatParser:

    _data_codes = {
        "tst": "task_state",
        "frx": "force_x_raw",
        "fry": "force_y_raw",
        "for": "force_y_raw",
        "frz": "force_z_raw",
        "fof": "cursor_position",
        "cur": "cursor_position",
        "rew": "reward",
        "stm": "stim",
        "per": "perturbation_offset",
        "frm": "photobox",
    }

    def __init__(
        self,
        file_path: str,
        sample_rate: int = 1000,
        success_state_name: str = "Success",
    ):
        """Class for parsing speedgoat files

        Args:
            file_path (str): path to file directory
            sample_rate (int, optional): task sample rate. Defaults to 1000.
            success_state_name (str, optional): name of task state indicating a successful trial. Defaults to "Success".
        """
        self.file_path = file_path
        self.sample_rate = sample_rate
        self.success_state_name = success_state_name
        self._set_file_names()
        self._set_task_states()
        self._hash_trial_files()
        self._ensure_complete_trial_files()

    # --- init methods ---
    def _set_file_names(self):
        self.file_names = [f for f in os.listdir(self.file_path)]

    def _set_task_states(self):
        "Reads task state definitions from the summary file"
        try:
            summary_file = next(
                f for f in self.file_names if re.match(r".*.summary", f)
            )
        except StopIteration:
            raise ValueError(f"Missing summary file in {self.file_path}")
        else:
            full_file = os.path.join(self.file_path, summary_file)
            with open(full_file, "r") as f:
                summary_text = f.read()
            keys, values = self._decode_speedgoat_text(summary_text)
            self.task_states = {}
            for key, value in zip(keys, values):
                m = re.match(r"TaskState(\d+)", key)
                if m is not None:
                    state_number = int(m.group(1))
                    state_name = value[1:-1]
                    self.task_states[state_name] = state_number
            assert (
                self.success_state_name in self.task_states
            ), f"Success state '{self.success_state_name}' not in task states"

    def _hash_trial_files(self):
        """Creates a nested dictionary of trial file names, 
        indexed by trial number, then file extension (e.g., 'data', 'params')"""
        trial_pattern = re.compile(r".*beh_(\d+).(\w+)")
        self.trial_files = defaultdict(dict)
        for f in self.file_names:
            m = trial_pattern.match(f)
            if m is not None:
                file_extension = m.group(2)
                trial_number = int(m.group(1))
                self.trial_files[trial_number][file_extension] = m.group(0)

    def _ensure_complete_trial_files(self):
        """Ensures each trial has a complete set of params and data files
        Removes any file names from dictionary without matching params and data files"""
        del_trials = []
        for trial_number, file_names in self.trial_files.items():
            for f_type in ["params", "data"]:
                if f_type not in file_names.keys():
                    print(f"Missing {f_type} for trial {trial_number}. Ignoring trial.")
                    del_trials.append(trial_number)
        for trial_number in del_trials:
            del self.trial_files[trial_number]

    # --- public methods ---
    def set_trial_data_and_params(self):
        """Helper method for creating a dictionary of matched trial params and data, since
        calling set_trial_params can skip trials due to missing params and
        calling set_trial_data can skip trials due to dropped packets or incomplete trials.
        """
        self.set_trial_params()
        self.set_trial_data()
        params_trials = set(trial for trial in self.trial_params.keys())
        data_trials = set(trial for trial in self.trial_data.keys())
        matched_trials = params_trials.union(data_trials)
        self.trial_params = {
            k: v for k, v in self.trial_params.items() if k in matched_trials
        }
        self.trial_data = {
            k: v for k, v in self.trial_data.items() if k in matched_trials
        }

    def set_trial_data(self):
        "Creates a dictionary of trial data for each trial"
        self.trial_data = {}
        for trial_number in self.trial_files.keys():
            trial_data = self.read_trial_data(trial_number)
            if trial_data is not None:
                self.trial_data[trial_number] = trial_data

    def set_trial_params(self):
        "Creates a dictionary of trial params for each trial"
        self.trial_params = {}
        for trial_number in self.trial_files.keys():
            params = self.read_trial_params(trial_number)
            if params is not None:
                self.trial_params[trial_number] = params

    def read_trial_data(self, trial_number: int):
        "Returns a dictionary of trial data for a given trial number"
        file_data = self._read_file_data(trial_number, "data")
        data = self._reshape_data_stream(file_data)
        simulation_time = self._read_simulation_time(data)
        if simulation_time is None:
            print(f"Ignoring trial {trial_number} due to dropped packets")
            return
        trial_data = {"simulation_time": simulation_time}
        trial_data = self._decode_data_stream(trial_data, data)
        trial_data = self._fill_missing_data(trial_data)
        is_success = self._get_trial_result(trial_data)
        if is_success is None:
            print(f"Trial {trial_number} was incomplete and excluded")
            return
        trial_data["successful_trial"] = is_success
        return trial_data

    def read_trial_params(self, trial_number: int):
        "Returns a dictionary of trial parameters for a given trial number"
        file_data = self._read_file_data(trial_number, "params")
        if len(file_data) == 0:
            print(f"Ignoring trial {trial_number} due to missing params")
            return
        params_text = "".join([chr(x) for x in file_data[N_CLOCK_BYTES:]])
        params = self._read_signed_params(params_text)
        params["type"] = "".join([chr(int(x)) for x in params["type"]])
        return params

    # --- helper methods ---
    def _decode_data_stream(self, trial_data: dict, data: np.ndarray):
        "Decodes trial data stream to extract trial data values"
        n_bytes_per_trial = len(data)
        idx = int(N_CLOCK_BYTES + N_LEN_BYTES)
        while idx < n_bytes_per_trial:
            d_code = "".join(
                [chr(x) for x in data[idx + np.r_[:N_CODE_BYTES], 0]]
            ).lower()
            d_len = int(data[1 + N_CODE_BYTES + idx + np.r_[:2], 0].view(np.uint16))
            d_type = chr(data[N_CODE_BYTES + idx, 0])
            if d_type == "D":
                d_bytes = 3 + N_CODE_BYTES + idx + np.r_[: d_len * 8]
                d_values = data[d_bytes, :].flatten("F").view(np.double)
                idx = 1 + d_bytes[-1]

            elif d_type == "U":
                d_bytes = 3 + N_CODE_BYTES + idx
                d_values = data[d_bytes, :].flatten("F")
                idx = 1 + d_bytes

            else:
                print(f"Unrecognized data type {d_type}")
                idx += 1
            try:
                d_name = self._data_codes[d_code]
            except KeyError:
                pass
            else:
                trial_data[d_name] = d_values
        return trial_data

    def _decode_speedgoat_text(self, text: str):
        "Standard function for decoding speedgoat parameter definitions"
        text = ";" + text
        keys = re.findall(";(.*?):=", text)
        values = re.findall(":=(.*?);", text)
        return keys, values

    def _fill_missing_data(self, trial_data: dict):
        """Ensures that trial data has an entry for every value in self._data_codes
        (for backwards compatability)"""
        n_samples = len(trial_data["simulation_time"])
        for code_value in self._data_codes.values():
            if code_value not in trial_data:
                trial_data[code_value] = np.repeat(np.nan, n_samples)
        return trial_data

    def _get_trial_result(self, trial_data: dict):
        "Returns True/False if a successful trial; None if incomplete"
        last_state = trial_data["task_state"][-1]
        success_state = self.task_states[self.success_state_name]
        if last_state < success_state:
            return None
        else:
            return True if last_state == success_state else False

    def _read_file_data(self, trial_number: int, file_type: str):
        "Returns the data stream for a params or data file"
        try:
            file_names = self.trial_files[trial_number]
        except KeyError:
            raise KeyError(f"Trial {trial_number} not in files")
        else:
            try:
                file_name = file_names[file_type]
            except KeyError:
                raise KeyError(f"File type {file_type} not in files")
            else:
                full_file = os.path.join(self.file_path, file_name)
                with open(full_file, "r") as f:
                    return np.fromfile(file=f, dtype=np.uint8)

    def _read_signed_params(self, params_text: str):
        "Parses the params text string and evaluates matrix strings as numeric"
        keys, values = self._decode_speedgoat_text(params_text)
        matrix_pattern = re.compile(r"(-?)(\[)(.*)(\])")
        params = {}
        for key, value in zip(keys, values):
            m = matrix_pattern.match(value)
            value_sign = m.group(1)
            value_nums = m.group(3)
            params[key] = eval(value_sign + value_nums)
        return params

    def _read_simulation_time(self, data: np.ndarray):
        "Reads simulation time from data stream and checks for missing packets"
        simulation_time = data[:N_CLOCK_BYTES, :].flatten("F").view(np.double)
        missing_packets = (
            (dt > int(0.5 * self.sample_rate)) and (dt < int(1.5 * self.sample_rate))
            for dt in np.diff(simulation_time)
        )
        if any(missing_packets):
            return None
        else:
            return simulation_time

    def _reshape_data_stream(self, file_data: np.ndarray):
        n_bytes_per_trial = int(
            N_CLOCK_BYTES
            + N_LEN_BYTES
            + np.uint16(file_data[N_CLOCK_BYTES : N_CLOCK_BYTES + 1])
        )
        return file_data.reshape((n_bytes_per_trial, -1), order="F")

