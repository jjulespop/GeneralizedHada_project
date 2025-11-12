'''Calculate solving results means, split by number of targets'''

import os
import sys
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


def check_validity(sol, time, memory, sol_sol, sol_time, sol_memory) -> bool:
    '''Calculate targets compliance and overall solution validity'''

    sol_compliance = (sol_sol - sol) / sol
    time_compliance = (sol_time - time) / time
    memory_compliance = (sol_memory - memory) / memory

    if (sol_compliance <= 0) and (time_compliance <= 0) and (memory_compliance <= 0):
        return True
    else:
        return False


def safe_div(a, b):
    return a / b if b != 0 else 0



if __name__ == '__main__':
    
    # loads path from config
    results_path = config['paths']['results']

    rules_types = enumerate(config['rules_types'])

    output_path_sol_presence = f"{results_path}/computations/results_presence_sol.csv"
    output_path_sol_validity = f"{results_path}/computations/results_validity_sol.csv"


    ### LOGIC RULES
    for idx, rule in rules_types:
        # initialize variables
        sol_found_tot = 0
        sol_valid_tot = 0
        count = 0

        # check result folder existance
        result_folder = f"{results_path}/{rule}_latest"
        if not os.path.exists(result_folder):
            print(f"Result file not found: {result_folder}")
            continue

        # iterate through all folder files
        for file in os.listdir(result_folder):
            result_df = pd.read_csv(f"{result_folder}/{file}")

            for idx, row in result_df.iterrows():

                sol_presence = False
                sol_validity = False

                # true values
                sol = row['sol']
                time = row['time']
                memory = row['memory']

                # predicted values
                sol_sol = row['sol_sol']
                sol_time = row['sol_time']
                sol_memory = row['sol_memory']

                # check solution presence and validity
                if pd.notna(sol_sol) and pd.notna(sol_time) and pd.notna(sol_memory):
                    sol_presence = True
                    sol_validity = check_validity(sol, time, memory, sol_sol, sol_time, sol_memory)

                # add to current total
                if sol_presence:
                    sol_found_tot += 1
                if sol_validity:
                    sol_valid_tot += 1
                count +=1

        # collect and save results
        new_data_presence = {
            "rule": rule,
            "sol_presence": safe_div(sol_found_tot, count)
        }

        new_data_validity = {
            "rule": rule,
            "sol_validity": safe_div(sol_valid_tot, count)
        }

        # create new dataframes
        results_presence = pd.DataFrame([new_data_presence])
        results_validity = pd.DataFrame([new_data_validity])

        fill_csv(output_path_sol_presence, results_presence)
        fill_csv(output_path_sol_validity, results_validity)     


    ### DECISION TREES
    sol_found_tot = 0
    sol_valid_tot = 0
    count = 0

    # check result folder existance
    result_folder = f"{results_path}/hada_latest"
    if not os.path.exists(result_folder):
        raise FileNotFoundError(f"Result folder not found: {result_folder}")

    # iterate through all folder files
    for file in os.listdir(result_folder):
        result_df = pd.read_csv(f"{result_folder}/{file}")

        for idx, row in result_df.iterrows():
            sol_presence = False
            sol_validity = False

            # true values
            sol = row['sol']
            time = row['time']
            memory = row['memory']

            # predicted values
            sol_sol = row['sol_sol']
            sol_time = row['sol_time']
            sol_memory = row['sol_memory']

            # check solution presence and validity
            if pd.notna(sol_sol) and pd.notna(sol_time) and pd.notna(sol_memory):
                sol_presence = True
                sol_validity = check_validity(sol, time, memory, sol_sol, sol_time, sol_memory)

            # add to current total
            if sol_presence:
                sol_found_tot += 1
            if sol_validity:
                sol_valid_tot += 1
            count +=1


    # collect and save results
    new_data_presence = {
        "rule": "decision_trees",
        "sol_presence": safe_div(sol_found_tot, count)
    }

    new_data_validity = {
        "rule": "decision_trees",
        "sol_validity": safe_div(sol_valid_tot, count)
    }

    # create new dataframes
    results_presence = pd.DataFrame([new_data_presence])
    results_validity = pd.DataFrame([new_data_validity])

    fill_csv(output_path_sol_presence, results_presence)
    fill_csv(output_path_sol_validity, results_validity) 