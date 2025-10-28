"""
Necessary to install package cplex.
Test class for HADA logic rules algorithm (one instance). Takes arguments from command line - necessary at least one to set
objective hyperparameter.

Default:
    - anticipate algorithm
    - gridrex rules type

"""

import time
import os
import sys
import pandas as pd
import argparse
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from hada.core.hada import HADA
from hada.core.config.configdb import ConfigDB
from hada.core.models.logic_models import LogicModels
from hada.core.optimization.optimization_request import OptimizationRequest
from hada.core.optimization.user_constraints import UserConstraints
from hada.core.optimization.hardware_prices import HardwarePrices
from hada.core.optimization.inputs import Inputs
from hada.core.config.datasets import Datasets
from hada.config import config_loader

config = config_loader.load_config(config_path="./hada/config/config.yaml")


if __name__ == "__main__":

    # load paths from config
    data_path = config["paths"]["data"]
    algorithms_configs_path = config["paths"]["algorithms_configs"]
    logic_rules_path = config["paths"]["logic_rules"]
    storage_ws_url = config["paths"]["storage_ws_url"]
    results_path = config['paths']['results']

    rules_type = config['rules_types']['gridrex']

    ### Init ###
    # db config
    db = ConfigDB.from_local(algorithms_configs_path)
    # db = ConfigDB.from_remote(storage_ws_url)

    # datasets config
    datasets = Datasets.from_local(db, data_path)
    # datasets = Datasets.from_remote(db, storage_ws_url)

    ### Parse command line args ###
    parser = argparse.ArgumentParser(description="Run optimization using HADA.")
    parser.add_argument("--instance", "-i", default = 0, type=int, help = "Validation set instance index.")
    parser.add_argument("--memory_bound", "-m", default = "100", help = "Memory constraint value or 'None'/'obj'.")
    parser.add_argument("--time_bound", "-t", default = "60", help = "Time constraint value or 'None'/'obj'.")
    parser.add_argument("--sol_bound", "-s", default = "60", help = "Solution constraint value or 'None'/'obj'.")
    parser.add_argument("--algorithm", "-a", default = "anticipate", help = "Algorithm name to use.")
    args = parser.parse_args()

    ### Extract argument values ###
    instance_index = args.instance
    algorithm = args.algorithm
    objective = None

    # parse bounds
    mem_bound = args.memory_bound
    if mem_bound == "None":
        mem_bound = None
    else:
        if mem_bound == "obj":
            objective = 'memory'
        else:
            mem_bound = int(mem_bound)

    time_bound = args.time_bound
    if time_bound == "None":
        time_bound = None
    else:
        if time_bound == "obj":
            objective = 'time'
        else:
            time_bound = int(time_bound)

    sol_bound = args.sol_bound
    if sol_bound == "None":
        sol_bound = None
    else:
        if sol_bound == "obj":
            objective = 'sol'
        else:
            sol_bound = int(sol_bound)

    if objective is None:
        raise ValueError("No objective specified - one of the bounds must be 'obj'")        

    print(f"\nSelected algorithm: {algorithm}")
    print(f"Objective: {objective}")
    print(f"Bounds -- Memory: {mem_bound}, Time: {time_bound}, Solution: {sol_bound}")

    ### Load logic models and validation set ###
    models = LogicModels(db, logic_rules_path, rules_type)
    validation_set = pd.read_csv(f"{data_path}/ValidationSet.csv")
    instance = validation_set.iloc[instance_index]
    print("\nSelected instance:")
    print(instance)

    ### Prepare user request ###
    # set user constraints
    user_constraints = UserConstraints(db, algorithm)
    if (time_bound is not None) and time_bound != "obj":
        user_constraints.add_constraint("time", "leq", time_bound)
    if (mem_bound is not None) and mem_bound != "obj":
        user_constraints.add_constraint("memory", "leq", mem_bound)
    if (sol_bound is not None) and sol_bound != "obj":
        user_constraints.add_constraint("sol", "leq", sol_bound)

    # set input values
    inputs = Inputs(db, algorithm)
    inputs.add_input("load_std", float(instance["load_std"]))
    inputs.add_input("load_mean", float(instance["load_mean"]))
    inputs.add_input("pv_std", float(instance["pv_std"]))
    inputs.add_input("pv_mean", float(instance["pv_mean"]))

    # set hw prices
    hws_prices = HardwarePrices(db, algorithm)
    hws_prices.add_hw_price("pc", 0)

    # create optimitazione request
    robustness_factor = 0.9
    request = OptimizationRequest(
                                db=db,
                                algorithm=algorithm,
                                target=objective,
                                objective="min",
                                robustness_factor=robustness_factor,
                                user_constraints=user_constraints,
                                hws_prices=hws_prices,
                                inputs=inputs
                            )

    ### Handling datasets and models ###
    # extract info from datasets
    var_bounds = datasets.get_var_bounds_all(request)
    robust_coeff = datasets.get_robust_coeff(models, request)

    ### Run optimization with HADA ###
    print("\nRunning optimization")
    start_time = time.time()
    solution = HADA(db, request, models, var_bounds, robust_coeff)
    execution_time = time.time() - start_time
    print("Optimization completed")

    ### Extract solution details ###
    n_vars = solution.num_variables
    n_constraints = solution.num_constraints

    if solution.targets_values:
        sol_sol = solution.targets_values.get("sol")
        sol_time = solution.targets_values.get("time")
        sol_memory = solution.targets_values.get("memory")
        sol_hyperparams = list(solution.hyperparams_values.values())[0]
    else:
        sol_sol = sol_time = sol_memory = sol_hyperparams = None

    print("\nOPTIMIZATION RESULTS")
    print(solution)

    ### Collect and save results ###
    new_data = {
        "ex_times": execution_time,
        "n_vars": n_vars,
        "n_constraints": n_constraints,
        "sol_sol": sol_sol,
        "sol_memory": sol_memory,
        "sol_time": sol_time,
        "sol_hyperparam": sol_hyperparams
    }

    results = pd.DataFrame([instance]).assign(**new_data)
    print("\nNew result entry:")
    print(results)

    # build file path
    file_name = (
        f"{results_path}/{str(rules_type).lower()}/results_{algorithm}_{objective}_"
        f"m{mem_bound}_t{time_bound}_s{sol_bound}.csv"
    )

    # append results or create new file
    if not os.path.exists(file_name):
        res_df = results
    else:
        res_df = pd.read_csv(file_name)
        res_df = pd.concat([res_df, results], ignore_index=True)

    # save to csv
    res_df.to_csv(path_or_buf=file_name, index=False)
    print(f"\nResults saved to: {file_name}")


