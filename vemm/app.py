#!/bin/python3
import os
import json
import traceback
from flask import Flask, request, session, render_template, jsonify
from vemm.core.configdb import ConfigDB
from vemm.core.datasets import Datasets
from vemm.core.ml_models import MLModels
from vemm.core.optimization_request import OptimizationRequest, UserConstraints, HardwarePrices, Inputs
from vemm.core.hada import HADA


# ==============================================================================
# Service setup
# ==============================================================================
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False
app.secret_key = ';u_QC&vzGaAR;&67vma[(4_cHZ;(F!;]dwjh&tJRBF;S(7aWYz/e=z!]^Fhk.K!@'

# ==============================================================================
# Init HADA
# ==============================================================================

# for local init modality
data_path_no_inp = 'algorithms/data/input-independent'
data_path_inp = 'algorithms/data/input-dependent'
configs_path_no_inp = 'algorithms/configs/input-independent'
configs_path_inp = 'algorithms/configs/input-dependent'
# for both init modalities
categories_path_no_inp = "algorithms/categorical_mappings/input-independent"
categories_path_inp = "algorithms/categorical_mappings/input-dependent"
models_path_no_inp = 'algorithms/models/input-independent'
models_path_inp = 'algorithms/models/input-dependent'

init_type = os.getenv('INIT_TYPE')
if init_type == 'local' or init_type is None:
    db = ConfigDB.from_local(configs_path_no_inp, configs_path_inp)
    datasets = Datasets.from_local(db, data_path_no_inp, data_path_inp, categories_path_no_inp, categories_path_inp)
elif init_type == 'remote':
    db = ConfigDB.from_remote('http://localhost:5333')
    datasets = Datasets.from_remote(db, 'http://localhost:5333', categories_path_no_inp, categories_path_inp)
else:
    raise AttributeError('Environment variable INIT_TYPE must be se to "local" or "remote"')

models = MLModels(db, datasets, models_path_no_inp, models_path_no_inp)

# ==============================================================================
# Utility functions
# ==============================================================================
def run_hada(optimization_request):
    
    var_bounds = datasets.get_var_bounds_all(optimization_request)
    robust_coeff = datasets.get_robust_coeff(models, optimization_request)

    solution = HADA(db, datasets, optimization_request, models, var_bounds, robust_coeff)
    return solution

def parse_request_form(algorithm, form_dict, input_dependent=False, inputs_file=None):

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

    #print(form_dict)
    user_constraints = UserConstraints(db, algorithm, input_dependent)
    for target in db.get_targets(algorithm, input_dependent):
        if form_dict[f'constraint_{target}'] != '':
            user_constraints.add_constraint(target,
                                            form_dict[f'constraint_{target}_type'],
                                            sanitize_field(form_dict[f'constraint_{target}']))

    hws_prices = HardwarePrices(db, algorithm, input_dependent)
    for hw in db.get_hws(algorithm, input_dependent):
        price = sanitize_field(form_dict[f'price_{hw}'])
        hws_prices.add_hw_price(hw, price)
    
    #if form_dict['input_case'] == 'input_dependent':
    opt_req_args = {'db': db,
                    'algorithm': algorithm,
                    'target': form_dict['target'],
                    'opt_type': form_dict['objective_type'],
                    'robustness_fact': sanitize_field(form_dict['robust_factor']),
                    'user_constraints': user_constraints,
                    'hws_prices': hws_prices}
 
    if input_dependent:
        inputs = Inputs(db, algorithm)
        if inputs_file:
            for input in inputs_file['inputs']:
                inputs.add_input(input['name'], input['value'])
        opt_req_args['inputs'] = inputs

    optimization_request = OptimizationRequest(**opt_req_args)

    return optimization_request

def parse_request_json(data):
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
        "inputs": [  # optional, only for input-dependent cases
        { 
        "name": "input_var_0", 
        "value": 32 
        }, 
        ... 
    ], 
    }
    '''
    input_dependent = 'inputs' in data

    inputs = None
    if input_dependent:
        inputs = Inputs(db, data['algorithm'])
        for input in data['inputs']:
            inputs.add_input(input['name'], input['value'])

    user_constraints = UserConstraints(db, data['algorithm'], input_dependent)
    for constraint in data['constraints']:
        user_constraints.add_constraint(constraint['target'],
                                        constraint['type'],
                                        constraint['value'])

    hws_prices = HardwarePrices(db, data['algorithm'], input_dependent)
    if 'price_per_hw' in data:
        for hw_price in data['price_per_hw']:
            hws_prices.add_hw_price(hw_price['hw'], hw_price['price'])


    optimization_request = OptimizationRequest(db=db,
                                               algorithm=data['algorithm'],
                                               target=data['objective']['target'],
                                               opt_type=data['objective']['type'],
                                               robustness_fact=data['robustness_fact'],
                                               user_constraints=user_constraints,
                                               hws_prices=hws_prices,
                                               inputs=inputs)
    return optimization_request



def format_solution(solution):
    sol_hyperparams = {hyperparam:val for hyperparam,val in solution.hyperparams_values.items()}
    sol_targets = {target:val for target,val in solution.targets_values.items()}
    out = {'hw': solution.chosen_hw, 'hyperparams': sol_hyperparams,'targets': sol_targets}

    return out

# ==============================================================================
# Routes (GUI)
# ==============================================================================
@app.route('/', methods=['GET', 'POST'])
def hada_gui():

    out = None
    # init algorithm selection
    if 'last_selected_algo' not in session:
        session['last_selected_algo'] = db.get_algorithms(input_dependent=False)[0]
        session['last_input_dependent'] = False
    try:
        # two separate forms, one for algorithm selection and one for optimization requests
        if request.method == 'POST':
            form_dict = request.form.to_dict()
            #print(form_dict)
            
            if form_dict['form_id'] == 'select_algo':
                # populating GUI
                session['last_input_dependent'] = form_dict['selected_input_dep'] == "True"
                session['last_selected_algo'] = form_dict['algorithm']


            if form_dict['form_id'] == 'optimize':
                # checking if input file is uploaded
                opt_args = {}
                if session['last_input_dependent']:
                    if 'fileUpload' in request.files and request.files['fileUpload'].filename != '':
                        inputs_file = json.loads(request.files['fileUpload'].read())
                        opt_args['inputs_file'] = inputs_file

                optimization_request = parse_request_form(session['last_selected_algo'],
                                                          form_dict, 
                                                          input_dependent=session['last_input_dependent'],
                                                          **opt_args)
                solution = run_hada(optimization_request)

                if solution:
                    out = format_solution(solution)
                else:
                    out = 'No solution.'

        # rendering
        lb_per_var, ub_per_var = datasets.extract_var_bounds(session['last_selected_algo'], session['last_input_dependent'])
        description_per_var = db.get_description_per_var(session['last_selected_algo'], session['last_input_dependent'])
        input_independent_algos = db.get_algorithms(input_dependent=False)
        input_dependent_algos = db.get_algorithms(input_dependent=True)
        #rendering_kwargs = {'algorithms': db.get_algorithms(input_dependent=session['last_input_dependent']),
        rendering_kwargs = {'algorithms': {'input-dependent': input_dependent_algos, 'input-independent': input_independent_algos},
                            'input_dependent': session['last_input_dependent'],
                            'targets': db.get_targets(session['last_selected_algo'], session['last_input_dependent']),
                            'price_per_hw': db.get_prices_per_hw(session['last_selected_algo'], session['last_input_dependent']),
                            'lb_per_var': lb_per_var,
                            'ub_per_var': ub_per_var,
                            'description_per_var': description_per_var}
                
        session['last_rendering_kwargs'] = rendering_kwargs
    except Exception as e:
        traceback.print_exc()
        out=str(e)

    return render_template('hada_gui.html',
                           **session['last_rendering_kwargs'],
                           selected_algo=session['last_selected_algo'],
                           out=out)

# ==============================================================================
# Routes (API)
# ==============================================================================
@app.route('/algorithms', methods=['GET'])
def get_algorithms():
    return jsonify({'algorithms':
                    {'input-independent': db.get_algorithms(input_dependent=False),
                    'input-dependent': db.get_algorithms(input_dependent=True)}})


@app.route('/algorithms/<algorithm>', methods=['GET'])
def get_algo_info(algorithm):

    cases = []
    if algorithm in db.get_algorithms(input_dependent=True):
        cases.append(('input-dependent', True))
    if algorithm in db.get_algorithms(input_dependent=False):
        cases.append(('input-independent', False))


    ret = {'algorithm': algorithm,
           'input-independent': None,
           'input-dependent': None}

    for name, input_dependent in cases:
        hyperparams = db.get_hyperparams(algorithm, input_dependent)
        # types are relevant only for hyperparameters, targets are assumed to be 'float'
        types = db.get_type_per_var(algorithm, input_dependent)
        targets = db.get_targets(algorithm, input_dependent)
        description_per_var = db.get_description_per_var(algorithm, input_dependent)
        lb_per_var, ub_per_var = datasets.extract_var_bounds(algorithm, input_dependent)
        lb_per_var['price'] = None
        ub_per_var['price'] = None
        description_per_var['price'] = None

        
        hyperparams_profiles = {hyperparam: {'description': description_per_var[hyperparam],
                                                        'type': types[hyperparam],
                                                        'lb': lb_per_var[hyperparam],
                                                        'ub': ub_per_var[hyperparam]}
                                for hyperparam in hyperparams}

        targets_profiles = {target: {'description': description_per_var[target],
                                                'lb': lb_per_var[target],
                                                'ub': ub_per_var[target]} 
                            for target in targets}

        hws_with_prices = {hw: {'default_price': price} 
                        for hw,price in db.get_prices_per_hw(algorithm, input_dependent).items()}

        case = {'hws': hws_with_prices,
                'hyperparameters': hyperparams_profiles,
                'targets': targets_profiles}
        
        # only for input-dependent cases
        if input_dependent:
            inputs = db.get_inputs(algorithm)
            inputs_profiles = {input: {'description': description_per_var[input],
                                   'type': types[input],
                                   'lb': lb_per_var[input],
                                   'ub': ub_per_var[input]}
                                    for input in inputs}
            case['inputs'] = inputs_profiles

        ret[name] = case

    return ret

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
    app.run()
