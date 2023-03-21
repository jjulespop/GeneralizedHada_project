import time
from core.hada import HADA
from core.configdb import ConfigDB
from core.optimization_request import OptimizationRequest, UserConstraints, HardwarePrices, Inputs
from core.datasets import Datasets
from core.ml_models import MLModels

if __name__ == '__main__':

    configs_path = './algorithms/configs'
    data_path = './algorithms/data'
    models_path = './algorithms/models'
    storage_ws_url = 'http://localhost:5333'

    ##### Init #####
    db = ConfigDB.from_local(configs_path)
    #db = ConfigDB.from_remote(storage_ws_url)

    datasets = Datasets.from_local(db, data_path)
    #datasets = Datasets.from_remote(db, storage_ws_url)

    models = MLModels(db, datasets, models_path)

    print(db.get_type_per_var('anticipate'))
    ##### Preparing a request #####
    # constraints can be added only for targets available to that algorithm
    user_constraints = UserConstraints(db, 'anticipate')
    #user_constraints.add_constraint('pv_mean', 'eq', 260)
    #user_constraints.add_constraint('pv_var', 'eq', 81000)
    #user_constraints.add_constraint('load_mean', 'eq', 260)
    #user_constraints.add_constraint('load_var', 'eq', 29000)
    user_constraints.add_constraint('memory', 'leq', 70)
    user_constraints.add_constraint('sol', 'leq', 400)
    inputs = Inputs(db, 'anticipate')
    inputs.add_input('load_var', 28000)
    inputs.add_input('load_mean',  314)
    inputs.add_input('pv_var',  76000)
    inputs.add_input('pv_mean',  268)
    # we have default values from configs (can be None); user can overwrite them; at the end no None values are accepted
    hws_prices = HardwarePrices(db, 'anticipate')
    hws_prices.add_hw_price('pc', 0)
    
    robustness_factor = 0

    request = OptimizationRequest(db, 'anticipate', 'time', inputs, 'min',  robustness_factor, user_constraints, hws_prices)

    print(request.inputs.get_inputs()["pv_var"])
    print(request.user_constraints.get_constraints()["memory"])
    ##### Handling datasets and models #####
    # extracting info from datasets
    var_bounds = datasets.get_var_bounds_all(request)
    print(var_bounds)
    robust_coeff = datasets.get_robust_coeff(models, request)
    print(robust_coeff)

    ##### Optimizing #####
    # submitting request to HADA
    solution = HADA(db, request, models, var_bounds, robust_coeff)
    print("solution")
    print(solution)
