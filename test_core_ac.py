import time
from core.hada import HADA
import multiprocessing as mp
from core.configdb import ConfigDB
from core.optimization_request import OptimizationRequest, UserConstraints, HardwarePrices, Inputs
from core.datasets import Datasets
from core.ml_models import MLModels
import tracemalloc
import time

def run_HADA(queue, db, request, models, var_bounds, robust_coeff):
    tracemalloc.start()
    start = time.time()
    solution = HADA(db, request, models, var_bounds, robust_coeff)
    ex_time = time.time() - start
    current_mem, peak_mem = tracemalloc.get_traced_memory()
    queue.put((solution, ex_time, peak_mem))


if __name__ == '__main__':
    tracemalloc.start()
    configs_path = './algorithms/configs'
    data_path = './algorithms/data'
    models_path = 'algorithms/models'
    storage_ws_url = 'http://localhost:5333'

    ##### Init #####
    db = ConfigDB.from_local(configs_path)
    #db = ConfigDB.from_remote(storage_ws_url)

    datasets = Datasets.from_local(db, data_path)
    #datasets = Datasets.from_remote(db, storage_ws_url)
    algorithm = 'contingency' # 'anticipate'#
    models = MLModels(db, datasets, models_path)

    print(db.get_type_per_var(algorithm))
    ##### Preparing a request #####
    # constraints can be added only for targets available to that algorithm
    user_constraints = UserConstraints(db, algorithm)
    user_constraints.add_constraint('memory', 'leq', 400)
    user_constraints.add_constraint('sol', 'leq', 400)
    user_constraints.add_constraint('sol', 'geq', 50)
    user_constraints.add_constraint('time', 'leq', 200)
    # setting input
    inputs = Inputs(db, algorithm)
    inputs.add_input('load_std', 167)
    inputs.add_input('load_mean',  314)
    inputs.add_input('pv_std',  276)
    inputs.add_input('pv_mean',  268)
    # we have default values from configs (can be None); user can overwrite them; at the end no None values are accepted
    hws_prices = HardwarePrices(db, algorithm)
    hws_prices.add_hw_price('pc', 0)
    
    robustness_factor = 0

    request = OptimizationRequest(db, algorithm, 'time', inputs, 'min',  robustness_factor, user_constraints, hws_prices)

    #print(request.inputs.get_inputs()["pv_std"])
    #print(request.user_constraints.get_constraints()["memory"])
    ##### Handling datasets and models #####
    # extracting info from datasets
    var_bounds = datasets.get_var_bounds_all(request)
    print(var_bounds)
    robust_coeff = None #datasets.get_robust_coeff(models, request)
    print(robust_coeff)

    ##### Optimizing #####
    # submitting request to HADA
    solution = HADA(db, request, models, var_bounds, robust_coeff)
    """queue = mp.Queue()
    process= mp.Process(target=run_HADA, args=(queue, db, request, models, var_bounds, robust_coeff))
    process.start()
    process.join()
    solution, ex_time, ex_memory = queue.get()"""
    print(tracemalloc.get_traced_memory())
    print("solution")
    print(solution)
    #print(ex_time)
    #print(ex_memory)
