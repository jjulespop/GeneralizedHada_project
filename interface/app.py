#!/bin/python3
import os
import sys
import logging
from flask import Flask, request, session, render_template, jsonify

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from hada.config import config_loader
import interface.utility as utility

config = config_loader.load_config(config_path="./hada/config/config.yaml")


# ==============================================================================
# Service setup
# ==============================================================================
app = Flask(__name__,
            template_folder=os.path.join(os.path.dirname(__file__), "templates"),
            static_folder=os.path.join(os.path.dirname(__file__), "static"))
app.secret_key = config['app']['secret_key']

logger = logging.getLogger(__name__)


# ==============================================================================
# Routes (GUI)
# ==============================================================================
@app.route('/', methods=['GET', 'POST'])
def hada_gui():

    out = None
    
    if 'last_selected_algo' not in session:
        session['last_selected_algo'] = utility.get_configdb().get_algorithms()[0]
    
    try:
        
        # two separate forms, one for algorithm selection and one for optimization requests
        if request.method == 'POST':
            form_dict = request.form.to_dict()
            
            if form_dict['form_id'] == 'select_algo':
                session['last_selected_algo'] = form_dict['algorithm']
            
            if form_dict['form_id'] == 'optimize':
                optimization_request = utility.parse_request_form(session['last_selected_algo'], form_dict)
                solution = utility.run_hada(optimization_request)
                out = utility.format_solution(solution)

        # rendering for both
        lb_per_var, ub_per_var = utility.get_datasets().extract_var_bounds(session['last_selected_algo'])
        description_per_var = utility.get_configdb().get_description_per_var(session['last_selected_algo'])
        
        rendering_kwargs = {
            'algorithms': utility.get_configdb().get_algorithms(),
            'targets': utility.get_configdb().get_targets(session['last_selected_algo']),
            'price_per_hw': utility.get_configdb().get_prices_per_hw(session['last_selected_algo']),
            'lb_per_var': lb_per_var,
            'ub_per_var': ub_per_var,
            'description_per_var': description_per_var
        }
        session['last_rendering_kwargs'] = rendering_kwargs

    except Exception as e:
        logger.exception(e)
        out = str(e)
        
        return render_template(
            'hada_gui.html',
            **session['last_rendering_kwargs'],
            selected_algo = session['last_selected_algo'],
            out = out
        )

    return render_template(
        'hada_gui.html',
        **rendering_kwargs,
        selected_algo = session['last_selected_algo'],
        out = out
    )



# ==============================================================================
# Routes (API)
# ==============================================================================
@app.route('/algorithms', methods=['GET'])
def get_algorithms():
    return jsonify({'algorithms': utility.get_configdb().get_algorithms()})


@app.route('/algorithms/<algorithm>', methods=['GET'])
def get_algo_info(algorithm):

    hyperparams = utility.get_configdb().get_hyperparams(algorithm)
    targets = utility.get_configdb().get_targets(algorithm)
    description_per_var = utility.get_configdb().get_description_per_var(algorithm)
    lb_per_var, ub_per_var = utility.get_datasets().extract_var_bounds(algorithm)
    lb_per_var['price'] = None
    ub_per_var['price'] = None
    description_per_var['price'] = None

    hyperparams_with_bounds_and_desc = {
        hyperparam: {
            'description': description_per_var[hyperparam],
            'lb': lb_per_var[hyperparam],
            'ub': ub_per_var[hyperparam]
        }
        for hyperparam in hyperparams
    }

    targets_with_bounds_and_desc = {
        target: {
            'description': description_per_var[target],
            'lb': lb_per_var[target],
            'ub': ub_per_var[target]
        } 
        for target in targets
    }

    hws_with_prices = {
        hw: {
            'default_price': price
        } 
        for hw,price in utility.get_configdb().get_prices_per_hw(algorithm).items()
    }

    ret = {
        'algorithm': algorithm,
        'hws': hws_with_prices,
        'hyperparameters': hyperparams_with_bounds_and_desc,
        'targets': targets_with_bounds_and_desc
    }

    # alternative
    #ret = {'algorithm': algorithm,
    #       'hyperparameters': hyperparams,
    #       'targets': targets,
    #       'bounds': {'lb_per_var': lb_per_var,
    #                   'ub_per_var': ub_per_var}}

    return jsonify(ret)


@app.route('/optimize', methods=['POST'])
def optimize():
    
    try:
        data = request.get_json()
        optimization_request = utility.parse_request_json(data)
        solution = utility.run_hada(optimization_request)

        ret = {'solution': None}
    
        if solution:
            ret = {'solution': utility.format_solution(solution)}

    except Exception as e:
        logger.exception(e)
        ret = {'error': str(e)}

    return jsonify(ret)



# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=5000, debug=True)