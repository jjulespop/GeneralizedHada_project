import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from hada.config import config_loader
from hada.core.config.configdb import ConfigDB
from hada.core.config.datasets import Datasets, DatasetsLocal
from hada.core.models.ml_models import MLModels
from hada.core.models.logic_models import LogicModels
from hada.core.optimization.optimization_request import OptimizationRequest
from hada.core.optimization.optimization_solution import OptimizationSolution
from hada.core.optimization.user_constraints import UserConstraints
from hada.core.optimization.hardware_prices import HardwarePrices
from hada.core.hada_iter import HADA


config = config_loader.load_config(config_path="./hada/config/config.yaml")


# ==============================================================================
# Init HADA
# ==============================================================================
data_path = config['paths']['data']
models_path = config['paths']['ml_models']
algorithms_configs_path = config['paths']['algorithms_configs']
logic_rules_path = config['paths']['logic_rules']
rules_type = config['rules_types']['cart']
storage_ws_url = config['paths']['storage_ws_url']
# remote_address = config['paths']['remote_address']

db = ConfigDB.from_local(algorithms_configs_path)
datasets: DatasetsLocal = Datasets.from_local(db, data_path)
# db = ConfigDB.from_remote(storage_ws_url)
# datasets = Datasets.from_remote(db, storage_ws_url)
# db = ConfigDB.from_remote(remote_address)
# datasets = Datasets.from_remote(db, remote_address)
ml_models = MLModels(db, datasets, models_path)
logic_models = LogicModels(db, logic_rules_path, rules_type)



# ==============================================================================
# Utility functions
# ==============================================================================
def get_configdb() -> ConfigDB:
    return db


def get_datasets() -> Datasets:
    return datasets


def run_hada(optimization_request):
    
    var_bounds = datasets.get_var_bounds_all(optimization_request)
    robust_coeff = datasets.get_robust_coeff(logic_models, optimization_request)

    solution = HADA(db, optimization_request, logic_models, var_bounds, robust_coeff)
    
    return solution


def sanitize_field(x):

    if x in (None, ''):
        return None
    try:
        return float(x)
    except ValueError:
        return x


### ROUTE GUI ###
def parse_request_form(algorithm: str, form_dict: dict) -> OptimizationSolution:
    """Parse GUI form data into a proper OptimizationRequest"""

    user_constraints = UserConstraints(db, algorithm)
    
    for target in db.get_targets(algorithm):
    
        if form_dict[f'constraint_{target}'] != '':
            user_constraints.add_constraint(
                target,
                form_dict[f'constraint_{target}_type'],
                sanitize_field(form_dict[f'constraint_{target}'])
            )

    hws_prices = HardwarePrices(db, algorithm)
    for hw in db.get_hws(algorithm):
        price = sanitize_field(form_dict[f'price_{hw}'])
        hws_prices.add_hw_price(hw, price)

    optimization_request = OptimizationRequest(db=db,
                                               algorithm=algorithm,
                                               target=form_dict['target'],
                                               objective=form_dict['objective_type'],
                                               robustness_factor=sanitize_field(form_dict['robust_factor']),
                                               user_constraints=user_constraints,
                                               hws_prices=hws_prices)
                                                
    return optimization_request


### ROUTE API ###
def parse_request_json(data) -> OptimizationRequest:
    """Parse JSON data into a proper OptimizationRequest"""

    user_constraints = UserConstraints(db, data['algorithm'])
    for constraint in data['constraints']:
        user_constraints.add_constraint(
            constraint['target'],
            constraint['type'],
            constraint['value']
        )

    hws_prices = HardwarePrices(db, data['algorithm'])
    if 'price_per_hw' in data:
        for hw_price in data['price_per_hw']:
            hws_prices.add_hw_price(
                hw_price['hw'], 
                hw_price['price']
            )

    optimization_request = OptimizationRequest(db=db,
                                               algorithm=data['algorithm'],
                                               target=data['objective']['target'],
                                               objective=data['objective']['type'],
                                               robustness_factor=data['robustness_fact'],
                                               user_constraints=user_constraints,
                                               hws_prices=hws_prices)
    
    return optimization_request


def format_solution(solution: OptimizationSolution) -> str | dict:
    """Format HADA solution for JSON output."""

    if solution is None:
        raise ValueError("format_solution: solution cannot be None")

    # extract and validate each field
    sol_hw = {}
    if solution.chosen_hw:
        sol_hw["hw"] = solution.chosen_hw

    sol_hyperparams = {}
    if solution.hyperparams_values:
        sol_hyperparams = {
            hyperparam: val
            for hyperparam, val in solution.hyperparams_values.items()
            if val is not None
        }

    sol_targets = {}
    if solution.targets_values:
        sol_targets = {
            target: val
            for target, val in solution.targets_values.items()
            if val is not None
        }

    # combine all valid parts
    out = {**sol_hw, **sol_hyperparams, **sol_targets}

    if not out:
        return str("No feasible solution found for the specified constraints")

    return out