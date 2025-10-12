#!/bin/python3
import os
import sys
from flask import Flask, request, session, render_template, jsonify
from hada.core.config.configdb import ConfigDB
from hada.core.config.datasets import Datasets, DatasetsLocal
from hada.core.models.ml_models import MLModels
from hada.core.models.logic_models import LogicModels
from hada.core.optimization.optimization_request import OptimizationRequest
from hada.core.optimization.user_constraints import UserConstraints
from hada.core.optimization.hardware_prices import HardwarePrices
from hada.core.hada import HADA


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from hada.config import config_loader

config = config_loader.load_config(config_path="./hada/config/config.yaml")


# ==============================================================================
# Service setup
# ==============================================================================
app = Flask(__name__)
app.secret_key = ';u_QC&vzGaAR;&67vma[(4_cHZ;(F!;]dwjh&tJRBF;S(7aWYz/e=z!]^Fhk.K!@'

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
def run_hada(optimization_request):
    
    var_bounds = datasets.get_var_bounds_all(optimization_request)
    robust_coeff = datasets.get_robust_coeff(logic_models, optimization_request)

    solution = HADA(db, optimization_request, logic_models, var_bounds, robust_coeff)
    return solution

def parse_request_form(algorithm, form_dict):

    #def sanitize_float(x):
    #    return None if x == '' else float(x)
    def sanitize_field(x):
        if x == '':
            return None
        try:
            x = float(x)
        except ValueError as e:
            pass

        return x

    user_constraints = UserConstraints(db, algorithm)
    for target in db.get_targets(algorithm):
        if form_dict[f'constraint_{target}'] != '':
            user_constraints.add_constraint(target,
                                            form_dict[f'constraint_{target}_type'],
                                            sanitize_field(form_dict[f'constraint_{target}']))

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

def parse_request_json(data) -> OptimizationRequest:
    '''
    Example:
    {
        "algorithm":"fwt",
        "robustness_fact": null,
        "objective": {"target":"memory", "type": "min"},
        "constraints": [
            {'target': 'time', 'type': 'leq', value: 120},
            ...
        ],
        price_per_hw: [
            {'hw':'pc', price: 30},
            ...
        ]
    }
    '''
    user_constraints = UserConstraints(db, data['algorithm'])
    for constraint in data['constraints']:
        user_constraints.add_constraint(constraint['target'],
                                        constraint['type'],
                                        constraint['value'])

    hws_prices = HardwarePrices(db, data['algorithm'])
    if 'price_per_hw' in data:
        for hw_price in data['price_per_hw']:
            hws_prices.add_hw_price(hw_price['hw'], hw_price['price'])


    optimization_request = OptimizationRequest(db=db,
                                               algorithm=data['algorithm'],
                                               target=data['objective']['target'],
                                               objective=data['objective']['type'],
                                               robustness_factor=data['robustness_fact'],
                                               user_constraints=user_constraints,
                                               hws_prices=hws_prices)
    return optimization_request



def format_solution(solution):
    sol_hw = {'hw': solution.chosen_hw}
    sol_hyperparams = {hyperparam:val for hyperparam,val in solution.hyperparams_values.items()}
    sol_targets = {target:val for target,val in solution.targets_values.items()}
    out = {**sol_hw, **sol_hyperparams, **sol_targets}

    return out

# ==============================================================================
# Routes (GUI)
# ==============================================================================
@app.route('/', methods=['GET', 'POST'])
def hada_gui():

    out = None
    if 'last_selected_algo' not in session:
        session['last_selected_algo'] = db.get_algorithms()[0]
    try:
        # two separate forms, one for algorithm selection and one for optimization requests
        if request.method == 'POST':
            form_dict = request.form.to_dict()
            
            if form_dict['form_id'] == 'select_algo':
                session['last_selected_algo'] = form_dict['algorithm']
            if form_dict['form_id'] == 'optimize':
                optimization_request = parse_request_form(session['last_selected_algo'], form_dict)
                solution = run_hada(optimization_request)

                if solution:
                    out = format_solution(solution)
                else:
                    out = 'No solution.'

        # rendering
        lb_per_var, ub_per_var = datasets.extract_var_bounds(session['last_selected_algo'])
        description_per_var = db.get_description_per_var(session['last_selected_algo'])
        rendering_kwargs = {'algorithms': db.get_algorithms(),
                            'targets': db.get_targets(session['last_selected_algo']),
                            'price_per_hw': db.get_prices_per_hw(session['last_selected_algo']),
                            'lb_per_var': lb_per_var,
                            'ub_per_var': ub_per_var,
                            'description_per_var': description_per_var}
        session['last_rendering_kwargs'] = rendering_kwargs

    except Exception as e:
        print(e)
        out=str(e)
        return render_template('hada_gui.html',
                               **session['last_rendering_kwargs'],
                               selected_algo=session['last_selected_algo'],
                               out=out)

    return render_template('hada_gui.html',
                           **rendering_kwargs,
                           selected_algo=session['last_selected_algo'],
                           out=out)

# ==============================================================================
# Routes (API)
# ==============================================================================
@app.route('/algorithms', methods=['GET'])
def get_algorithms():
    return jsonify({'algorithms': db.get_algorithms()})

@app.route('/algorithms/<algorithm>', methods=['GET'])
def get_algo_info(algorithm):

    hyperparams = db.get_hyperparams(algorithm)
    targets = db.get_targets(algorithm)
    description_per_var = db.get_description_per_var(algorithm)
    lb_per_var, ub_per_var = datasets.extract_var_bounds(algorithm)
    lb_per_var['price'] = None
    ub_per_var['price'] = None
    description_per_var['price'] = None

    
    hyperparams_with_bounds_and_desc = {hyperparam: {'description': description_per_var[hyperparam],
                                                     'lb': lb_per_var[hyperparam],
                                                     'ub': ub_per_var[hyperparam]}
                               for hyperparam in hyperparams}

    targets_with_bounds_and_desc = {target: {'description': description_per_var[target],
                                             'lb': lb_per_var[target],
                                             'ub': ub_per_var[target]} 
                           for target in targets}

    hws_with_prices = {hw: {'default_price': price} 
                       for hw,price in db.get_prices_per_hw(algorithm).items()}

    ret = {'algorithm': algorithm,
           'hws': hws_with_prices,
           'hyperparameters': hyperparams_with_bounds_and_desc,
           'targets': targets_with_bounds_and_desc}

    # alternative
    #ret = {'algorithm': algorithm,
    #       'hyperparameters': hyperparams,
    #       'targets': targets,
    #       'bounds': {'lb_per_var': lb_per_var,
    #                   'ub_per_var': ub_per_var}}

    return jsonify(ret)

@app.route('/optimize', methods=['POST'])
def optimize():
    data = request.get_json()
    try:
        optimization_request = parse_request_json(data)
        solution = run_hada(optimization_request)

        ret = {'solution': None}
        if solution:
            ret = {'solution': format_solution(solution)}

    except Exception as e:
        print(e)
        ret = {'error': str(e)}

    return jsonify(ret)



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)