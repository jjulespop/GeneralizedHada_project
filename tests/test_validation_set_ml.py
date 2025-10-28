"""
Usage of mprof command - needs to be installed.
Test class for HADA decision tree algorithm with all the instances of the Validation Set, running the
test_one_instance_dt.py script.

    - anticipate or contingency algorithms

"""

import os
import sys
import time
import subprocess
import glob
import pandas as pd
import numpy as np

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from hada.core.config.configdb import ConfigDB
from hada.config import config_loader

config = config_loader.load_config(config_path="./hada/config/config.yaml")


def read_mem_file():
    """
    Reads the memory profile file created by `mprof`, extracts the mean and max memory usage,
    then deletes the file to keep the workspace clean.

    Returns:
        tuple (float, float): (mean_memory, max_memory)
    """

    files = glob.glob('mprofile_*')
    if not files:
        raise FileNotFoundError("No mprofile_* file found after running mprof.")

    file_name = files[0]
    with open(file_name) as f:
        lines = f.readlines()

    # parse memory data
    mem_values = []
    for line in lines[1:]:
        parts = line.split()
        if len(parts) > 1:
            try:
                mem_values.append(float(parts[1]))
            except ValueError:
                continue

    if not mem_values:
        raise ValueError(f"No memory data found in {file_name}.")

    mean_mem = np.mean(mem_values)
    max_mem = np.max(mem_values)

    os.remove(file_name)

    return mean_mem, max_mem


if __name__ == '__main__':

    # load paths from config
    data_path = config['paths']['data']
    algorithms_configs_path = config['paths']['algorithms_configs']
    python_script = "tests/test_one_instance_ml.py"

    validation_set = pd.read_csv(f"{data_path}/ValidationSet.csv")

    ### Define variable bounds ###
    bounds = {
        "sol": [250, 313, 339, 362, 392, None],
        "memory": [59, 86, 87, 140, 241, None],
        "time": [1, 21, 40, 58, 150, None],
    }

    ### Init ###
    # db config
    db = ConfigDB.from_local(algorithms_configs_path)

    targets = ['sol', 'time', 'memory']

    ### Experiments for each algorithm and objective ###
    for algorithm in ['anticipate', 'contingency']:
        for objective in targets:

            # create a copy of bounds excluding the current objective
            other_bounds = bounds.copy()
            other_bounds.pop(objective)
            bound_targets = list(other_bounds.keys())

            for first_bound in other_bounds[bound_targets[0]]:
                for second_bound in other_bounds[bound_targets[1]]:
                    current_bounds = {
                        objective: "obj",
                        bound_targets[0]: first_bound,
                        bound_targets[1]: second_bound,
                    }

                    mem_bound = current_bounds["memory"]
                    sol_bound = current_bounds["sol"]
                    time_bound = current_bounds["time"]

                    # set result file path
                    result_file = (
                        f'./hada/results/results_{algorithm}_{objective}_'
                        f'm{mem_bound}_t{time_bound}_s{sol_bound}.csv'
                    )

                    ex_memory_mean = []
                    ex_memory_max = []

                    print(f"\nRunning {algorithm} | objective: {objective} | "
                          f"m={mem_bound}, t={time_bound}, s={sol_bound}")

                    # run script test_one_instance.py for each instance in the validation set
                    for idx, instance in validation_set.iterrows():
                        start_time = time.time()
                        process = subprocess.Popen(
                            [f"mprof run {python_script} -a {algorithm} -i {str(idx)} -t {str(time_bound)} -m {str(mem_bound)} -s {str(sol_bound)}"],
                            shell=True)
                        process.wait()

                        # read mprof result file
                        try:
                            mean_mem, max_mem = read_mem_file()
                        except Exception as e:
                            print(f"Failed to read memory file for instance {idx}: {e}")
                            mean_mem, max_mem = np.nan, np.nan

                        ex_memory_mean.append(mean_mem)
                        ex_memory_max.append(max_mem)
                        print(f"Instance {idx} done in {time.time() - start_time:.2f}s")

                    ### Update result file with memory stats ###
                    if not os.path.exists(result_file):
                        print(f"Result file not found: {result_file}")
                        continue

                    result_df = pd.read_csv(result_file)
                    result_df = result_df.assign(
                                                ex_memory_mean=ex_memory_mean,
                                                ex_memory_max=ex_memory_max
                                            )
                    result_df.to_csv(result_file, index=False)
                    print(f"Updated {result_file} with memory usage statistics")
