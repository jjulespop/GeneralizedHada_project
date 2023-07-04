import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from vemm.core.hada import HADA
from vemm.core.configdb import ConfigDB
from vemm.core.optimization_request import OptimizationRequest, UserConstraints, HardwarePrices
from vemm.core.datasets import Datasets
from vemm.core.ml_models import MLModels

if __name__ == '__main__':

    categories_path_no_inp = "./vemm/algorithms/categorical_mappings/input-independent"
    categories_path_inp = "./vemm/algorithms/categorical_mappings/input-dependent"
    models_path_no_inp = './vemm/algorithms/models/input-independent'
    models_path_inp = './vemm/algorithms/models/input-dependent'
    storage_ws_url = 'http://localhost:5333'

    ##### Init #####
    #db = ConfigDB.from_local(configs_path)
    db = ConfigDB.from_remote(storage_ws_url)

    datasets = Datasets.from_remote(db, storage_ws_url, categories_path_no_inp, categories_path_inp)

    models = MLModels(db, datasets, models_path_no_inp, models_path_inp)

    print(db.get_type_per_var('toyalg'))
    ##### Preparing a request #####
    # constraints can be added only for targets available to that algorithm
    user_constraints = UserConstraints(db, 'toyalg')
    user_constraints.add_constraint('memory', 'leq', 50)
    user_constraints.add_constraint('price', 'leq', 250)

    # we have default values from configs (can be None); user can overwrite them; at the end no None values are accepted
    hws_prices = HardwarePrices(db, 'toyalg')
    hws_prices.add_hw_price('pc', 100)
    hws_prices.add_hw_price('g100', 200)
    hws_prices.add_hw_price('vm', 300)
    
    robustness_factor = None

    request = OptimizationRequest(db, 'toyalg', 'time', 'min', robustness_factor, user_constraints, hws_prices)

    ##### Handling datasets and models #####
    # extracting info from datasets
    var_bounds = datasets.get_var_bounds_all(request)
    print(var_bounds)

    robust_coeff = datasets.get_robust_coeff(models, request)
    print(robust_coeff)

    ##### Optimizing #####
    # submitting request to HADA
    solution = HADA(db, request, models, var_bounds, robust_coeff)
    print(solution)
