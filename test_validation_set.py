import pandas as pd
import subprocess
import glob
import os
import numpy as np

from core.configdb import ConfigDB


def read_mem_file():
    """reads and deletes the file with memory information created by mprof, returns mean and max"""
    file_name = glob.glob('mprofile_*')[0]
    with open(file_name) as f:
        lines = f.readlines()
    mems = []
    for line in lines[1:]:
        splitted = line.split(" ")
        mems.append(float(splitted[1]))
    mean = np.mean(mems)
    max = np.max(mems)
    os.remove(file_name)
    return mean, max


#to improve
if __name__ == '__main__':

    configs_path = './algorithms/configs'
    data_path = './algorithms/data'
    validation_set = pd.read_csv("algorithms/data/ValidationSet.csv")
    configs_path = './algorithms/configs'
    #bounds = {"time": [60, 120, 180, 300, None], 'memory': [100, 200, 300, 350, None], 'sol': [300, 340, 380, 420, None]}
    #bounds = {"sol": [250, 314, 340, 363, 393, 538], 'memory': [59, 87, 88, 141, 241, 343], 'time': [1, 22, 41, 59, 151, 349]}
    #bounds = {"sol": [250, 314, 340, 363, 393, 538], 'memory': [88], 'time': [1, 22, 41, 59, 151, 349]}
    bounds = {"sol": [250, 314, 340, 363, 393, None], 'memory': [59, 87, 88, 141, 241, None], 'time': [1, 22, 41, 59, 151, None]}
    #bounds = {"sol": [250, 313, 339, 362, 392, None], 'memory': [59, 86, 87, 140, 241, None], 'time': [1, 21, 40, 58, 150, None]}
    #bounds = {"sol": [250, 313, 339, 362, 392, None], 'memory': [59, 86, 87, 140, 241, None],
    #          'time': [1, 21, 40, 58, 150, None]}
    #bounds = {"time": [None], 'memory': [None], 'sol': [None]}
    db = ConfigDB.from_local(configs_path)
    #targets = db.get_targets('anticipate')
    #targets.pop()#removes price
    targets = ['sol', 'time', 'memory']
    for algorithm in ['anticipate', 'contingency']:
        for objective in targets:
            new_bounds = bounds.copy()
            new_bounds.pop(objective)
            bound_targets = list(new_bounds.keys())
            current_bounds = {objective: "obj"}
            for first_bound in new_bounds[bound_targets[0]]:
                current_bounds[bound_targets[0]] = first_bound
                for second_bound in new_bounds[bound_targets[1]]:
                    """if first_bound is not None:
                        current_bounds[bound_targets[1]] = None
                    else:
                        if second_bound is None:
                            continue
                        current_bounds[bound_targets[1]] = second_bound"""
                    current_bounds[bound_targets[1]] = second_bound
                    """if first_bound is not None and second_bound is not None:
                       continue"""
                    mem_bound = current_bounds["memory"]
                    sol_bound = current_bounds["sol"]
                    time_bound = current_bounds["time"]
                    file_name = f'algorithms/results/results_{algorithm}_{objective}_m{mem_bound}_t{time_bound}_s{sol_bound}.csv'
                    ex_memory_mean = []
                    ex_memory_max = []
                    for index, instance in validation_set.iterrows():
                        # run
                        process = subprocess.Popen(
                            ["mprof", "run", "test_one_instance.py", "-a", algorithm, "-i", str(index), "-t",
                             str(time_bound), "-m", str(mem_bound),
                             "-s", str(sol_bound)],
                            shell=True)
                        process.wait()
                        mean_mem, max_mem = read_mem_file()
                        ex_memory_max.append(max_mem)
                        ex_memory_mean.append(mean_mem)


                    new_columns = {'ex_memory_mean': ex_memory_mean, 'ex_memory_max': ex_memory_max}
                    # print(new_columns)
                    result_df = pd.read_csv(file_name)
                    new_df = result_df.assign(**new_columns)
                    new_df.to_csv(path_or_buf=file_name, index=False)
                    """if first_bound is not None:
                        break"""


