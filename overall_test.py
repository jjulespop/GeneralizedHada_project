import time
from hada_new import HADA
from configdb import ConfigDB
from optimization_request import OptimizationRequest, UserConstraints, HardwarePrices
from datasets import Datasets
from ml_models import MLModels

if __name__ == '__main__':

    configs_path = '../algorithms/configs'
    data_path = '../algorithms/data'
    models_path = '../algorithms/models'

    db = ConfigDB(configs_path)
    datasets = Datasets(db, data_path)
    models = MLModels(db, models_path)





    ##### Preparing a request #####
    user_constraints = UserConstraints(db, 'fwt')
    user_constraints.add_constraint('memory', 'leq', 30)
    user_constraints.add_constraint('price', 'leq', 120)

    hws_prices = HardwarePrices(db, 'fwt')
    #print(hws_prices.get_prices_per_hw())
    hws_prices.add_hw_price('pc', 100)
    hws_prices.add_hw_price('g100', 100)
    #hws_prices.add_hw_price('vm', 200)
    hws_prices.add_hw_price('vm', 100)
    
    robustness_factor = 0.5

    request = OptimizationRequest(db, 'fwt', 'time', 'min', robustness_factor, user_constraints, hws_prices)


    
    ##### Handling datasets and models #####
    # extracting info from datasets and handling ML models
    var_bounds = datasets.extract_var_bounds(request)
    print(var_bounds)

    robust_coeff = datasets.extract_robust_coeff(models, request)
    print(robust_coeff)

    # submitting request to HADA
    #HADA(algorithm, objective, user_constraint, price, var_bounds, mlmodel_files, export_log=False, robust_coeff=None):
    
    # Response (solution or not at least...) is another class probably... HADA could be just a function...

    # for now ignore logging
    ##### Optimizing #####
    s = time.time()
    solution, mdl = HADA(db, request, models, var_bounds, robust_coeff)
    print(time.time()-s)
    print(solution)

    #response = HADA(request, models, var_bounds, robust_coeff, logging=False) -
    # how to handle logging? Fixed log folder, a file for each request (e.g. %datetime.log)