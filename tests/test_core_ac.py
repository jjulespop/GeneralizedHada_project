"""
Testing HADA core logic with:

    - anticipate algorithm
    - CART rules type
    - logic models

Can be used for both HADA and HADA iterative version.

"""

import os
import sys
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from hada.core.hada_iter import HADA

from hada.core.config.configdb import ConfigDB
from hada.core.optimization.optimization_request import OptimizationRequestTest
from hada.core.optimization.user_constraints import UserConstraints
from hada.core.optimization.hardware_prices import HardwarePrices
from hada.core.optimization.inputs import Inputs
from hada.core.config.datasets import Datasets
from hada.core.models.logic_models import LogicModels
from hada.config import config_loader

config = config_loader.load_config(config_path="./hada/config/config.yaml")


if __name__ == "__main__":

    # load paths from config
    data_path = config["paths"]["data"]
    algorithms_configs_path = config["paths"]["algorithms_configs"]
    logic_rules_path = config["paths"]["logic_rules"]
    storage_ws_url = config["paths"]["storage_ws_url"]

    ### Init ###
    # db config
    db = ConfigDB.from_local(algorithms_configs_path)
    # db = ConfigDB.from_remote(storage_ws_url)

    # datasets config
    datasets = Datasets.from_local(db, data_path)
    # datasets = Datasets.from_remote(db, storage_ws_url)

    algorithm = config["algorithms"]["anticipate"]
    rules_type = config["rules_types"]["cart"]
    logic_models = LogicModels(db, logic_rules_path, rules_type)

    print(db.get_type_per_var(algorithm))

    ### Prepare user request ###
    # set user constraints
    user_constraints = UserConstraints(db, algorithm)
    user_constraints.add_constraint("memory", "leq", 350)
    user_constraints.add_constraint("time", "leq", 200)
    # additional constraints:
    # user_constraints.add_constraint("sol", "leq", 400)
    # user_constraints.add_constraint("sol", "geq", 50)

    # set input values
    inputs = Inputs(db, algorithm)
    inputs.add_input("load_std", 167)
    inputs.add_input("load_mean", 314)
    inputs.add_input("pv_std", 276)
    inputs.add_input("pv_mean", 268)

    # set hw prices
    hws_prices = HardwarePrices(db, algorithm)
    hws_prices.add_hw_price("pc", 0)

    # create optimitazione request
    robustness_factor = 0.2
    request = OptimizationRequestTest(
                                    db=db,
                                    algorithm=algorithm,
                                    target="sol",
                                    inputs=inputs,
                                    objective="min",
                                    robustness_factor=robustness_factor,
                                    user_constraints=user_constraints,
                                    hws_prices=hws_prices
                                )

    ### Handling datasets and models ###
    # extract info from datasets
    var_bounds = datasets.get_var_bounds_all(request)
    robust_coeff = datasets.get_robust_coeff(logic_models, request)
    print("Robustness coefficients:", robust_coeff)

    ### Run optimization with HADA ###
    solution = HADA(db, request, logic_models, var_bounds, robust_coeff)

    print("\nSOLUTION")
    print(solution)

    # analyze results
    data = datasets.get_dataset(algorithm, "pc")
    rules = logic_models.get_rules(algorithm, "pc", "sol")

