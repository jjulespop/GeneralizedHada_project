#!/bin/python3
import os
import json
from flask import Flask, request, session, render_template, jsonify
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
app.secret_key = ';u_QC&vzGaAR;&67vma[(4_cHZ;(F!;]dwjh&tJRBF;S(7aWYz/e=z!]^Fhk.K!@'

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

    var_bounds = datasets.get_var_bounds_all(optimization_request)
    robust_coeff = datasets.get_robust_coeff(models, optimization_request)

    solution = HADA(db, optimization_request, models, var_bounds, robust_coeff)
    return solution

def parse_request(algorithm, form_dict):

    def sanitize_float(x):
        return None if x == '' else float(x)

    hws_prices = HardwarePrices(db, algorithm)
    for hw in db.get_hws(algorithm):
        hws_prices.add_hw_price(hw, sanitize_float(form_dict[f'price_{hw}']))

    user_constraints = UserConstraints(db, algorithm)
    for target in db.get_targets(algorithm):
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

def format_solution(solution):
    sol_hw = {'hw': solution.chosen_hw}
    sol_hyperparams = {hyperparam:val for hyperparam,val in solution.hyperparams_values.items()}
    sol_targets = {target:val for target,val in solution.targets_values.items()}
    out = {**sol_hw, **sol_hyperparams, **sol_targets}

    return out

# ==============================================================================
# Routes
# ==============================================================================

@app.route('/', methods=['GET', 'POST'])
def hada_gui():

    out = None
    if not session['last_selected_algo']:
        session['last_selected_algo'] = db.get_algorithms()[0]
    try:
        # two separate forms, one for algorithm selection and one for optimization requests
        if request.method == 'POST':
            form_dict = request.form.to_dict()
            
            if form_dict['form_id'] == 'select_algo':
                session['last_selected_algo'] = form_dict['algorithm']
            if form_dict['form_id'] == 'optimize':
                solution = run_hada(session['last_selected_algo'], form_dict)

                if solution:
                    out = format_solution(solution)
                else:
                    out = 'No solution.'

        # rendering
        lb_per_var, ub_per_var = datasets.extract_var_bounds(session['last_selected_algo'])
        rendering_kwargs = {'algorithms': db.get_algorithms(),
                            'targets': db.get_targets(session['last_selected_algo']),
                            'price_per_hw': db.get_prices_per_hw(session['last_selected_algo']),
                            'lb_per_var': lb_per_var,
                            'ub_per_var': ub_per_var}
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
