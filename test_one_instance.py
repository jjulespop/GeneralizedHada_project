import time
from core.hada import HADA
from core.configdb import ConfigDB
from core.logic_models import LogicModels
from core.optimization_request import OptimizationRequest, UserConstraints, HardwarePrices, Inputs
from core.datasets import Datasets
import pandas as pd
import argparse
import os


if __name__ == '__main__':

    configs_path = './algorithms/configs'
    data_path = './algorithms/data'
    models_path = './algorithms/logic_rules'
    storage_ws_url = 'http://localhost:5333'

    ##### Init #####
    db = ConfigDB.from_local(configs_path)
    # db = ConfigDB.from_remote(storage_ws_url)

    datasets = Datasets.from_local(db, data_path)
    # datasets = Datasets.from_remote(db, storage_ws_url)
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--instance', '-i', default=0, type=int)
    parser.add_argument('--memory_bound', '-m', default="100")
    parser.add_argument('--time_bound', '-t', default="60")
    parser.add_argument('--sol_bound', '-s', default="60")
    parser.add_argument('--algorithm', '-a', default='anticipate')
    args = parser.parse_args()
    instance_index = args.instance
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
    algorithm = args.algorithm
    print(algorithm)
    file_name = f'algorithms/results/results_{algorithm}_{objective}_m{mem_bound}_t{time_bound}_s{sol_bound}.csv'
    models = LogicModels(db,  models_path, 'GridEx')
    validation_set = pd.read_csv("algorithms/data/ValidationSet.csv")
    instance = validation_set.iloc[instance_index]
    print(instance)
    user_constraints = UserConstraints(db, algorithm)
    ##### Preparing a request #####
    # constraints can be added only for targets available to that algorithm
    if (time_bound is not None) and time_bound != "obj":
        user_constraints.add_constraint('time', 'leq', time_bound)
    if (mem_bound is not None) and mem_bound != "obj":
        user_constraints.add_constraint('memory', 'leq', mem_bound)
    if (sol_bound is not None) and sol_bound != "obj":
        user_constraints.add_constraint('sol', 'leq', sol_bound)
    inputs = Inputs(db, algorithm)

    inputs.add_input('load_std', float(instance['load_std']))
    inputs.add_input('load_mean', float(instance['load_mean']))
    inputs.add_input('pv_std', float(instance['pv_std']))
    inputs.add_input('pv_mean', float(instance['pv_mean']))
    # we have default values from configs (can be None); user can overwrite them; at the end no None values are accepted
    hws_prices = HardwarePrices(db, algorithm)
    hws_prices.add_hw_price('pc', 0)
    robustness_factor = None
    request = OptimizationRequest(db, algorithm, objective, inputs, 'min', robustness_factor, user_constraints,
                                                  hws_prices)
    ##### Handling datasets and models #####
     # extracting info from datasets
    var_bounds = datasets.get_var_bounds_all(request)
     #print(var_bounds)
    robust_coeff = None #datasets.get_robust_coeff(models, request)
    #print(robust_coeff)

    ##### Optimizing #####
    # submitting request to HADA
    start = time.time()
    solution = HADA(db, request, models, var_bounds, robust_coeff)
    ex_time = time.time() - start

    n_vars = solution.num_variables
    n_constraints = solution.num_constraints
    if solution.targets_values:
        sol_sol = solution.targets_values.get("sol")
        sol_time = solution.targets_values.get("time")
        sol_memory = solution.targets_values.get("memory")
        sol_hyperparams = list(solution.hyperparams_values.values())[0]
    else:
        sol_sol = None
        sol_time = None
        sol_memory = None
        sol_hyperparams = None

    print("solution")
    print(solution)
    new_data = {'ex_times': ex_time,  'n_vars': n_vars, 'n_constraints': n_constraints,
                      'sol_sol': sol_sol, 'sol_memory': sol_memory, 'sol_time': sol_time, 'sol_hyperparam': sol_hyperparams}
                #print(new_columns)
    results = pd.DataFrame([instance])
    results = results.assign(**new_data)
    print(results)
    if not os.path.exists(file_name):
        res_df = results
    else:
        res_df = pd.read_csv(file_name)
        res_df = pd.concat([res_df, results], ignore_index=True)
    #print(res_df)
    res_df.to_csv(path_or_buf=file_name, index=False)

