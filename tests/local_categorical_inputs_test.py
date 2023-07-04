import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from vemm.core.hada import HADA
from vemm.core.configdb import ConfigDB
from vemm.core.optimization_request import OptimizationRequest, UserConstraints, HardwarePrices, Inputs
from vemm.core.datasets import Datasets
from vemm.core.ml_models import MLModels

if __name__ == '__main__':

    input_dependent=True
    configs_path_no_inp = './vemm/algorithms/configs/input-independent'
    configs_path_inp = './vemm/algorithms/configs/input-dependent'
    data_path_no_inp = './vemm/algorithms/data/input-independent'
    data_path_inp = './vemm/algorithms/data/input-dependent'
    categories_path_no_inp = "./vemm/algorithms/categorical_mappings/input-independent"
    categories_path_inp = "./vemm/algorithms/categorical_mappings/input-dependent"
    models_path_no_inp = './vemm/algorithms/models/input-independent'
    models_path_inp = './vemm/algorithms/models/input-dependent'
    #storage_ws_url = 'http://localhost:5333'

    ##### Init #####
    db = ConfigDB.from_local(configs_path_no_inp, configs_path_inp)
    #db = ConfigDB.from_remote(storage_ws_url)

    datasets = Datasets.from_local(db, data_path_no_inp, data_path_inp, categories_path_no_inp, categories_path_inp)
    #datasets = Datasets.from_remote(db, storage_ws_url)

    models = MLModels(db, datasets, models_path_no_inp, models_path_inp)

    ##### Preparing a request #####
    # inputs
    inputs = Inputs(db, 'toyalgstr')
    inputs.add_input('inp_0', 'a')

    # constraints can be added only for targets available to that algorithm
    user_constraints = UserConstraints(db, 'toyalgstr', input_dependent)
    user_constraints.add_constraint('time', 'leq', 120)

    # we have default values from configs (can be None); user can overwrite them; at the end no None values are accepted
    hws_prices = HardwarePrices(db, 'toyalgstr', input_dependent)
    hws_prices.add_hw_price('vm', 300)
    
    robustness_factor = 0.5

    request = OptimizationRequest(db, 'toyalgstr', 'memory', 'min', robustness_factor, user_constraints, hws_prices, inputs)

    ##### Handling datasets and models #####
    # extracting info from datasets
    var_bounds = datasets.get_var_bounds_all(request)
    #print(var_bounds)

    robust_coeff = datasets.get_robust_coeff(models, request)
    #print(robust_coeff)

    ##### Optimizing #####
    # submitting request to HADA
    solution = HADA(db, datasets, request, models, var_bounds, robust_coeff)
    print(solution)
