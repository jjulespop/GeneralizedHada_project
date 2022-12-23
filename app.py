#!/bin/python3
import os
import json
from flask import Flask, request, render_template, jsonify
from core.configdb import ConfigDB
from core.datasets import Datasets
from core.ml_models import MLModels
from core.optimization_request import OptimizationRequest, UserConstraints, HardwarePrices
from core.hada import HADA
# ==============================================================================
# Service setup
# ==============================================================================

# Build the Flask app
app = Flask(__name__)

# ==============================================================================
# Init HADA
# ==============================================================================
db = ConfigDB('algorithms/configs')
datasets = Datasets(db, 'algorithms/data')
models = MLModels(db, 'algorithms/models')

# ==============================================================================
# Utility functions
# ==============================================================================
def run_hada(algorithm, form_dict):

    # Merging form args and JSON configuration
    optimization_request = parse_request(algorithm, form_dict)
    print(vars(optimization_request))

    var_bounds = datasets.extract_var_bounds(optimization_request)
    robust_coeff = datasets.extract_robust_coeff(models, optimization_request)

    solution = HADA(db, optimization_request, models, var_bounds, robust_coeff)
    print(solution)
    return solution

def parse_request(algorithm, form_dict):

    def sanitize_float(x):
        return None if x == '' else float(x)

    hws_prices = HardwarePrices(db, algorithm)
    for hw in db.get_hws(algorithm):
        hws_prices.add_hw_price(hw, sanitize_float(form_dict[f'price_{hw}']))

    user_constraints = UserConstraints(db, algorithm)
    for target in db.get_targets(algorithm) + ['price']:
        if form_dict[f'constraint_{target}'] != '':
            user_constraints.add_constraint(target,
                                           form_dict[f'constraint_{target}_type'],
                                           sanitize_float(form_dict[f'constraint_{target}']))

    optimization_request = OptimizationRequest(db=db,
                                               algorithm=algorithm,
                                               target=form_dict['target'],
                                               opt_type=form_dict['objective_type'],
                                               robustness_fact=sanitize_float(form_dict['robust_factor']),
                                               user_constraints=user_constraints,
                                               hws_prices=hws_prices)

                                                
    return optimization_request

'''
def format_solution(params, solution):
    pass
'''

# ==============================================================================
# Routes
# ==============================================================================

@app.route('/', methods=['GET', 'POST'])
def hada_gui(selected_algo=db.get_algorithms()[0]):

    out = None

    if request.method == 'POST':
        try:
            form_dict = request.form.to_dict()
            #print(form_dict) 
            if form_dict['form_id'] == 'select_algo':
                selected_algo = form_dict['algorithm']
            elif form_dict['form_id'] == 'optimize':
                out = run_hada(selected_algo, form_dict)

                # HADA returned no solution
                if not out:
                    out = 'No solution.'

        except Exception as e:
            out=e

    rendering_kwargs = {'algorithms': db.get_algorithms(),
                        'targets': db.get_targets(selected_algo),
                        'price_per_hw': db.get_prices_per_hw(selected_algo)}

    return render_template('hada_gui.html',
                            **rendering_kwargs,
                            selected_algo=selected_algo,
                            out=out)


