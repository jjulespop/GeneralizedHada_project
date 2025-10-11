"""
Testing error differences between prediction values and real values for an algorithm target variables.

    - anticipate or contingency algorithm
    - CART rules type

"""

import os
import sys
import pandas

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from hada.core.configdb import ConfigDB
from hada.core.logic_models import LogicModels
from hada.config import config_loader

config = config_loader.load_config(config_path="./hada/config/config.yaml")


if __name__ == "__main__":

    # load paths from config
    algorithms_configs_path = config['paths']['algorithms_configs']
    logic_rules_path = config['paths']['logic_rules']
    results_path = config['paths']['results']

    ### Define variable bounds ###
    # bounds = {
    #     "time": [60, 120, 180, 300, None], 
    #     "memory": [100, 200, 300, 350, None], 
    #     "sol": [300, 340, 380, 420, None]
    # }
    # bounds = {
    #     "sol": [250, 314,   340,  363, 393, None], 
    #     "memory": [59, 87, 88, 141, 241,  None], 
    #     "time": [1,  22, 41, 59, 151,  None]
    # }

    bounds = {
        "sol": [250, 313, 339, 362, 392, None],
        "memory": [59, 86, 87, 140, 241, None],
        "time": [1, 21, 40, 58, 150, None]
    }

    targets = ["sol", "time", "memory"]
    rules_type = config['rules_types']['cart']

    ### Init ###
    # db config
    db = ConfigDB.from_local(algorithms_configs_path)
    # logic rules init
    lr = LogicModels(db, logic_rules_path, rules_type)

    # initialize stats
    stats = {}
    counter = {}
    similar = 0
    different = 0

    ### Algorithms iteration ###
    for algorithm in ["anticipate", "contingency"]:
        stats[algorithm] = {
            "ex_times": 0,
            "n_vars": 0,
            "n_constraints": 0,
            "ex_memory_mean": 0,
            "ex_memory_max": 0
        }
        counter[algorithm] = 0

        # load rules for each target variable
        rules = {target: lr.get_rules(algorithm, "pc", target) for target in targets}

        ### Objectives iteration ###
        for objective in targets:
            # create a shallow copy of bounds and remove the current objective
            new_bounds = dict(bounds)
            new_bounds.pop(objective)

            bound_targets = list(new_bounds.keys())
            current_bounds = {objective: "obj"}

            ### Bounds combination double iteration  ###
            for i, first_bound in enumerate(new_bounds[bound_targets[0]]):
                current_bounds[bound_targets[0]] = first_bound

                for j, second_bound in enumerate(new_bounds[bound_targets[1]]):
                    current_bounds[bound_targets[1]] = second_bound

                    mem_bound = current_bounds["memory"]
                    sol_bound = current_bounds["sol"]
                    time_bound = current_bounds["time"]

                    # path to the result file
                    file_name = (
                        f"{results_path}/{str(rules_type).lower()}/results_{algorithm}_{objective}_"
                        f"m{mem_bound}_t{time_bound}_s{sol_bound}.csv"
                    )

                    # load and process data from csv
                    df = pandas.read_csv(file_name)
                    sol_hp = df["sol_hyperparam"]
                    sol_time = df["sol_time"]
                    sol_memory = df["sol_memory"]
                    sol_sol = df["sol_sol"]

                    # define input variables
                    input_data = df[
                        ["load_mean", "load_std", "sol_hyperparam", "pv_mean", "pv_std"]
                    ]

                    # rename hyperparameter column based on algorithm type
                    if algorithm == "anticipate":
                        input_data = input_data.rename(columns={"sol_hyperparam": "nScenarios"})
                    elif algorithm == "contingency":
                        input_data = input_data.rename(columns={"sol_hyperparam": "nTraces"})

                    # prediction using logic models 
                    pred_sol = lr.predict(rules["sol"], input_data)
                    pred_time = lr.predict(rules["time"], input_data)
                    pred_memory = lr.predict(rules["memory"], input_data)

                    # predictions comparison to actual values
                    for idx in range(30):
                        diff_sol = float(pred_sol[idx]) - float(sol_sol[idx])
                        diff_time = float(pred_time[idx]) - float(sol_time[idx])
                        diff_memory = float(pred_memory[idx]) - float(sol_memory[idx])

                        # consider results "different" if any diff exceeds threshold
                        if (abs(diff_sol) >= 0.1 or abs(diff_memory) >= 0.1 or abs(diff_time) >= 0.1):
                            print("\nDIFFERENT")
                            print(f"Algorithm: {algorithm}, Objective: {objective}, Row: {idx}")
                            print(f"Bounds -> First: {first_bound}, Second: {second_bound}")
                            print(f"sol: {sol_sol[idx]} vs {pred_sol[idx]}  diff={diff_sol:.4f}")
                            print(f"time: {sol_time[idx]} vs {pred_time[idx]}  diff={diff_time:.4f}")
                            print(f"memory: {sol_memory[idx]} vs {pred_memory[idx]}  diff={diff_memory:.4f}")
                            print("-" * 60)
                            different += 1
                        else:
                            similar += 1

    ### Analyze results ###
    print("\nSUMMARY")
    print(f"Similar results: {similar}")
    print(f"Different results: {different}")
