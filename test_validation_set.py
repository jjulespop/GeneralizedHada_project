import time
from core.hada import HADA
from core.configdb import ConfigDB
from core.optimization_request import OptimizationRequest, UserConstraints, HardwarePrices, Inputs
from core.datasets import Datasets
from core.logic_models import LogicModels
import tracemalloc
import pandas as pd

#to inprove
if __name__ == '__main__':
    configs_path = './algorithms/configs'
    data_path = './algorithms/data'
    models_path = 'algorithms/logic_rules'
    storage_ws_url = 'http://localhost:5333'

    ##### Init #####
    db = ConfigDB.from_local(configs_path)
    # db = ConfigDB.from_remote(storage_ws_url)

    datasets = Datasets.from_local(db, data_path)
    # datasets = Datasets.from_remote(db, storage_ws_url)

    models = LogicModels(db, models_path)
    validation_set = pd.read_csv("algorithms/data/ValidationSet.csv")
    tracemalloc.start()
    for algorithm in ['anticipate', 'contingency']:
        ex_times = []
        ex_memory = []
        sol_time= []
        sol_sol = []
        sol_memory = []
        sol_hyperparams = []
        n_vars = []
        n_constraints = []
        for index, instance in validation_set.iterrows():
            ##### Preparing a request #####
            # constraints can be added only for targets available to that algorithm
            user_constraints = UserConstraints(db, algorithm)
            user_constraints.add_constraint('memory', 'leq', 100)
            user_constraints.add_constraint('time', 'leq', 30)
            #user_constraints.add_constraint('sol', 'leq', 500)
            inputs = Inputs(db, algorithm)
            inputs.add_input('load_std', float(instance['load_std']))
            inputs.add_input('load_mean', float(instance['load_mean']))
            inputs.add_input('pv_std', float(instance['pv_std']))
            inputs.add_input('pv_mean', float(instance['pv_mean']))
            # we have default values from configs (can be None); user can overwrite them; at the end no None values are accepted
            hws_prices = HardwarePrices(db, algorithm)
            hws_prices.add_hw_price('pc', 0)
            robustness_factor = None
            request = OptimizationRequest(db, algorithm, 'sol', inputs, 'min', robustness_factor, user_constraints,
                                          hws_prices)

            #print(request.inputs.get_inputs()["pv_std"])
            #print(request.user_constraints.get_constraints()["memory"])
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
            current_mem, peak_mem = tracemalloc.get_traced_memory()
            #tracemalloc.clear_traces()
            ex_memory.append(peak_mem)
            ex_times.append(ex_time)
            if solution:
                n_vars.append(solution.num_variables)
                n_constraints.append(solution.num_constraints)
                sol_sol.append(solution.targets_values.get("sol"))
                sol_time.append(solution.targets_values.get("time"))
                sol_memory.append(solution.targets_values.get("memory"))
                sol_hyperparams.append(list(solution.hyperparams_values.values())[0])
            else:
                n_vars.append(None)
                n_constraints.append(None)
                sol_sol.append(None)
                sol_time.append(None)
                sol_memory.append(None)
                sol_hyperparams.append(None)
            print(instance)
            print(ex_time)
            print("solution")
            print(solution)
        new_columns = {'ex_times': ex_times, 'ex_memory': ex_memory, 'n_vars': n_vars, 'n_constraints': n_constraints,
                      'sol_sol': sol_sol, 'sol_memory': sol_memory, 'sol_time': sol_time, 'sol_hyperparam': sol_hyperparams}
        #print(new_columns)
        new_df = validation_set.assign(**new_columns)
        new_df.to_csv(path_or_buf="algorithms/data/results_"+algorithm+".csv", index=False)
current_mem, peak_mem = tracemalloc.get_traced_memory()
print(peak_mem)
