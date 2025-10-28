"""
Testing HADA core logic with:

    - toyalg algorithm
    - ML models
"""

import os
import sys
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from hada.core.hada_ml import HADA
from hada.core.config.configdb import ConfigDB
from hada.core.optimization.optimization_request import OptimizationRequest
from hada.core.optimization.user_constraints import UserConstraints
from hada.core.optimization.hardware_prices import HardwarePrices
from hada.core.optimization.inputs import Inputs
from hada.core.config.datasets_ml import Datasets
from hada.core.models.ml_models import MLModels
from hada.config import config_loader

config = config_loader.load_config(config_path="./hada/config/config.yaml")


if __name__ == "__main__":

    # load paths from config
    data_path = config["paths"]["data"]
    models_path = config["paths"]["ml_models"]
    algorithms_configs_path = config["paths"]["algorithms_configs"]
    categories_path = config["paths"]["categorical_mappings"]
    storage_ws_url = config["paths"]["storage_ws_url"]

    ### Init ###
    # db config
    db = ConfigDB.from_local(algorithms_configs_path)
    # db = ConfigDB.from_remote(storage_ws_url)

    # datasets config
    datasets = Datasets.from_local(db, data_path, categories_path)
    # datasets = Datasets.from_remote(db, storage_ws_url)

    algorithm = config["algorithms"]["anticipate"]
    models = MLModels(db, datasets, models_path)

    print(db.get_type_per_var("toyalg"))

    ### Prepare user request ###
    # set user constraints
    user_constraints = UserConstraints(db, algorithm)
    user_constraints.add_constraint("memory", "leq", 350)
    user_constraints.add_constraint("time", "leq", 200)
    user_constraints.add_constraint("price", "leq", 250)

    # set input values
    inputs = Inputs(db, algorithm)
    inputs.add_input("load_std", 167)
    inputs.add_input("load_mean", 314)
    inputs.add_input("pv_std", 276)
    inputs.add_input("pv_mean", 268)

    # set hw prices
    hws_prices = HardwarePrices(db, "toyalg")
    hws_prices.add_hw_price("pc", 100)
    hws_prices.add_hw_price("g100", 200)
    hws_prices.add_hw_price("vm", 300)

    # create optimitazione request
    robustness_factor = 0.2
    request = OptimizationRequest(
                                db=db,
                                algorithm=algorithm,
                                target="sol",
                                objective="min",
                                robustness_factor=robustness_factor,
                                user_constraints=user_constraints,
                                hws_prices=hws_prices,
                                inputs=inputs
                            )

    ### Handling datasets and models ###
    # extract info from datasets
    var_bounds = datasets.get_var_bounds_all(request)
    print("Variable bounds:", var_bounds)

    robust_coeff = datasets.get_robust_coeff(models, request)
    print("Robustness coefficients:", robust_coeff)

    ### Run optimization with HADA ###
    solution = HADA(db, datasets, request, models, var_bounds, robust_coeff)

    print("\nSOLUTION")
    print(solution)

