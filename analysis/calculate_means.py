'''Calculate solving results means, split by number of targets'''

import os
import sys
import re
import math
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from hada.config import config_loader

config = config_loader.load_config(config_path="./hada/config/config.yaml")



def fill_csv(output_path: str, results: pd.DataFrame) -> None:
    '''Create new csv result file or append results to existing one'''
    
    # append results or create new file
    if not os.path.exists(output_path):
        res_df = results
    else:
        res_df = pd.read_csv(output_path)
        res_df = pd.concat([res_df, results], ignore_index=True)

    # save to csv
    res_df.to_csv(path_or_buf=output_path, index=False)
    print(f"\nResults saved to: {output_path}")



if __name__ == '__main__':

    # loads path from config
    results_path = config['paths']['results']

    rules_types = enumerate(config['rules_types'])

    output_path_time = f"{results_path}/computations/results_time.csv"
    output_path_vars = f"{results_path}/computations/results_vars.csv"
    output_path_constraints = f"{results_path}/computations/results_constraints.csv"
    output_path_memory_max = f"{results_path}/computations/results_max_memory.csv"
    output_path_memory_mean = f"{results_path}/computations/results_mean_memory.csv"

    # regex
    pattern_one_none = r'(None.*){1}'
    pattern_two_none = r'(None.*){2}'


    ### LOGIC RULES
    for idx, rule in rules_types:
        # initialize variables
        ex_times_mean_tot = [0, 0, 0]
        n_vars_mean_tot = [0, 0, 0]
        n_constraints_mean_tot = [0, 0, 0]
        memory_mean_tot = [0, 0, 0]
        memory_max_tot = [0, 0, 0]
        count = [0, 0, 0]

        # check result folder existance
        result_folder = f"{results_path}/{rule}_latest"
        if not os.path.exists(result_folder):
            print(f"Result file not found: {result_folder}")
            continue

        # iterate through all folder files
        for file in os.listdir(result_folder):
            result_df = pd.read_csv(f"{result_folder}/{file}")

            # compute mean for ex_times, n_vars, n_constraints, ex_memory_mean, ex_memory_max
            ex_times_mean = result_df['ex_times'].mean()
            n_vars_mean = result_df['n_vars'].mean()
            n_constraints_mean = result_df['n_constraints'].mean()
            memory_mean_mean = result_df['ex_memory_mean'].mean()
            memory_max_mean = result_df['ex_memory_max'].mean()

            ### match to correct number of targets
            # single target
            if re.match(pattern_two_none, file):
                # add to current total
                ex_times_mean_tot[0] += ex_times_mean
                n_vars_mean_tot[0] += n_vars_mean
                n_constraints_mean_tot[0] += n_constraints_mean
                memory_max_tot[0] += memory_max_mean
                memory_mean_tot[0] += memory_mean_mean
                count[0] +=1
            # two targets
            elif re.match(pattern_one_none, file):
                ex_times_mean_tot[1] += ex_times_mean
                n_vars_mean_tot[1] += n_vars_mean
                n_constraints_mean_tot[1] += n_constraints_mean
                memory_max_tot[1] += memory_max_mean
                memory_mean_tot[1] += memory_mean_mean
                count[1] +=1
            # three targets
            else:
                ex_times_mean_tot[2] += ex_times_mean
                n_vars_mean_tot[2] += n_vars_mean
                n_constraints_mean_tot[2] += n_constraints_mean
                memory_max_tot[2] += memory_max_mean
                memory_mean_tot[2] += memory_mean_mean
                count[2] +=1

        # collect and save results
        new_data_time = {
            "rule": rule,
            "ex_times_mean_1_target": (ex_times_mean_tot[0]/count[0]),
            "ex_times_mean_2_target": (ex_times_mean_tot[1]/count[1]),
            "ex_times_mean_3_target": (ex_times_mean_tot[2]/count[2])
        }

        new_data_vars = {
            "rule": rule,
            "n_vars_mean_1_target": int(math.ceil((n_vars_mean_tot[0]/count[0]))),
            "n_vars_mean_2_target": int(math.ceil((n_vars_mean_tot[1]/count[1]))),
            "n_vars_mean_3_target": int(math.ceil((n_vars_mean_tot[2]/count[2])))
        }

        new_data_constraints = {
            "rule": rule,
            "n_constraints_mean_1_target": int(math.ceil((n_constraints_mean_tot[0])/count[0])),
            "n_constraints_mean_2_target": int(math.ceil((n_constraints_mean_tot[1])/count[1])),
            "n_constraints_mean_3_target": int(math.ceil((n_constraints_mean_tot[2])/count[2]))
        }

        new_data_memory_mean = {
            "rule": rule,
            "memory_mean_mean_1_target": int(math.ceil((memory_mean_tot[0])/count[0])),
            "memory_mean_mean_2_target": int(math.ceil((memory_mean_tot[1])/count[1])),
            "memory_mean_mean_3_target": int(math.ceil((memory_mean_tot[2])/count[2]))
        }

        new_data_memory_max = {
            "rule": rule,
            "memory_max_mean_1_target": int(math.ceil((memory_max_tot[0])/count[0])),
            "memory_max_mean_2_target": int(math.ceil((memory_max_tot[1])/count[1])),
            "memory_max_mean_3_target": int(math.ceil((memory_max_tot[2])/count[2]))
        }

        # create new dataframes
        results_time = pd.DataFrame([new_data_time])
        results_vars = pd.DataFrame([new_data_vars])
        results_constraints = pd.DataFrame([new_data_constraints])
        results_memory_mean = pd.DataFrame([new_data_memory_mean])
        results_memory_max = pd.DataFrame([new_data_memory_max])

        fill_csv(output_path_time, results_time)
        fill_csv(output_path_vars, results_vars)
        fill_csv(output_path_constraints, results_constraints)
        fill_csv(output_path_memory_mean, results_memory_mean)
        fill_csv(output_path_memory_max, results_memory_max)


    ### DECISION TREES
    ex_times_mean_tot = [0, 0, 0]
    n_vars_mean_tot = [0, 0, 0]
    n_constraints_mean_tot = [0, 0, 0]
    memory_mean_tot = [0, 0, 0]
    memory_max_tot = [0, 0, 0]
    count = [0, 0, 0]

    # check result folder existance
    result_folder = f"{results_path}/hada_latest"
    if not os.path.exists(result_folder):
        raise FileNotFoundError(f"Result folder not found: {result_folder}")

    # iterate through all folder files
    for file in os.listdir(result_folder):
        result_df = pd.read_csv(f"{result_folder}/{file}")

        # compute mean for ex_times, n_vars, n_constraints, ex_memory_mean, ex_memory_max
        ex_times_mean = result_df['ex_times'].mean()
        n_vars_mean = result_df['n_vars'].mean()
        n_constraints_mean = result_df['n_constraints'].mean()
        memory_mean_mean = result_df['ex_memory_mean'].mean()
        memory_max_mean = result_df['ex_memory_max'].mean()

        ### match to correct number of targets
        # single target
        if re.match(pattern_two_none, file):
            # add to current total
            ex_times_mean_tot[0] += ex_times_mean
            n_vars_mean_tot[0] += n_vars_mean
            n_constraints_mean_tot[0] += n_constraints_mean
            memory_max_tot[0] += memory_max_mean
            memory_mean_tot[0] += memory_mean_mean
            count[0] +=1
        # two targets
        elif re.match(pattern_one_none, file):
            ex_times_mean_tot[1] += ex_times_mean
            n_vars_mean_tot[1] += n_vars_mean
            n_constraints_mean_tot[1] += n_constraints_mean
            memory_max_tot[1] += memory_max_mean
            memory_mean_tot[1] += memory_mean_mean
            count[1] +=1
        # three targets
        else:
            ex_times_mean_tot[2] += ex_times_mean
            n_vars_mean_tot[2] += n_vars_mean
            n_constraints_mean_tot[2] += n_constraints_mean
            memory_max_tot[2] += memory_max_mean
            memory_mean_tot[2] += memory_mean_mean
            count[2] +=1


    # collect and save results
    new_data_time = {
        "rule": "decision_trees",
        "ex_times_mean_1_target": (ex_times_mean_tot[0]/count[0]),
        "ex_times_mean_2_target": (ex_times_mean_tot[1]/count[1]),
        "ex_times_mean_3_target": (ex_times_mean_tot[2]/count[2])
    }

    new_data_vars = {
        "rule": "decision_trees",
        "n_vars_mean_1_target": int(math.ceil((n_vars_mean_tot[0]/count[0]))),
        "n_vars_mean_2_target": int(math.ceil((n_vars_mean_tot[1]/count[1]))),
        "n_vars_mean_3_target": int(math.ceil((n_vars_mean_tot[2]/count[2])))
    }

    new_data_constraints = {
        "rule": "decision_trees",
        "n_constraints_mean_1_target": int(math.ceil((n_constraints_mean_tot[0])/count[0])),
        "n_constraints_mean_2_target": int(math.ceil((n_constraints_mean_tot[1])/count[1])),
        "n_constraints_mean_3_target": int(math.ceil((n_constraints_mean_tot[2])/count[2]))
    }

    new_data_memory_mean = {
        "rule": "decision_trees",
        "memory_mean_mean_1_target": int(math.ceil((memory_mean_tot[0])/count[0])),
        "memory_mean_mean_2_target": int(math.ceil((memory_mean_tot[1])/count[1])),
        "memory_mean_mean_3_target": int(math.ceil((memory_mean_tot[2])/count[2]))
    }

    new_data_memory_max = {
        "rule": "decision_trees",
        "memory_max_mean_1_target": int(math.ceil((memory_max_tot[0])/count[0])),
        "memory_max_mean_2_target": int(math.ceil((memory_max_tot[1])/count[1])),
        "memory_max_mean_3_target": int(math.ceil((memory_max_tot[2])/count[2]))
    }

    # create new dataframes
    results_time = pd.DataFrame([new_data_time])
    results_vars = pd.DataFrame([new_data_vars])
    results_constraints = pd.DataFrame([new_data_constraints])
    results_memory_mean = pd.DataFrame([new_data_memory_mean])
    results_memory_max = pd.DataFrame([new_data_memory_max])

    fill_csv(output_path_time, results_time)
    fill_csv(output_path_vars, results_vars)
    fill_csv(output_path_constraints, results_constraints)
    fill_csv(output_path_memory_mean, results_memory_mean)
    fill_csv(output_path_memory_max, results_memory_max)

    