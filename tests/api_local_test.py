import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from vemm.core.hada import HADA
from vemm.core.configdb import ConfigDB
from vemm.core.optimization_request import OptimizationRequest, UserConstraints, HardwarePrices
from vemm.core.datasets import Datasets
from vemm.core.ml_models import MLModels
from vemm.utils.generate_post_request import *

if __name__ == '__main__':

    configs_path_no_inp = './vemm/algorithms/configs/input-independent'
    configs_path_inp = './vemm/algorithms/configs/input-dependent'
    data_path_no_inp = './vemm/algorithms/data/input-independent'
    data_path_inp = './vemm/algorithms/data/input-dependent'
    categories_path_no_inp = "./vemm/algorithms/categorical_mappings/input-independent"
    categories_path_inp = "./vemm/algorithms/categorical_mappings/input-dependent"
    models_path_no_inp = './vemm/algorithms/models/input-independent'
    models_path_inp = './vemm/algorithms/models/input-dependent'

    ##### Init #####
    db = ConfigDB.from_local(configs_path_no_inp, configs_path_inp)

    datasets = Datasets.from_local(db, data_path_no_inp, data_path_inp, categories_path_no_inp, categories_path_inp)

    models = MLModels(db, datasets, models_path_no_inp, models_path_inp)

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

    #test
    print(hws_prices.get_prices_per_hw())
    
    robustness_factor = None

    request = OptimizationRequest(db, 'toyalg', 'time', 'min', robustness_factor, user_constraints, hws_prices)

    json_request = generate_json_optimization_request(request)
    print(json_request)
    solution = submit_json_optimization_request(json_request)
    print(solution.text)