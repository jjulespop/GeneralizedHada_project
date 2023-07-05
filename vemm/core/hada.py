import docplex
from eml.backend import cplex_backend
from eml.tree.reader.sklearn_reader import read_sklearn_tree
from eml.tree import embed 
from docplex.mp.model_reader import ModelReader
from vemm.core.configdb import ConfigDB
from vemm.core.datasets import Datasets
from vemm.core.optimization_request import OptimizationSolution

def HADA(db : ConfigDB,
         datasets : Datasets,
         request,
         models,
         var_bounds,
         robust_coeff):
    '''
    Implement HADA:
        1. Declare variables and basic constraints
        2. Embed predictive models 
        3. Declare user-defined constraints and objective 
        4. Solve the model and output an optimal matching (hw-platform, alg-configuration)
    
    PARAMETERS
    ---------
    db : an instance of class core.configdb.ConfigDB
    datasets : an instance of class core.datasets.Datasets
    request : an instance of class core.optimizationrequest.OptimizationRequest
    models : an instance of class core.mlmodels.MLModels
    var_bounds : a dict with upper and lower bound for each variable
    robust_coeff : a dict with robustness coefficient to apply for each pair (hardware, target)

    RETURN
    ------
    sol : a dict with the solution found, or None if no solution is found 
    '''

    ####### MODEL #######
    bkd = cplex_backend.CplexBackend()
    mdl = docplex.mp.model.Model("HADA")
    #mdl.parameters.mip.tolerances.integrality = 0.0

    hws = db.get_hws(request.algorithm, request.input_dependent)
    targets = set(list(request.user_constraints.get_constraints().keys()) + [request.target])
    
    # Expand data objects with one-hot encoded categorical variables
    str_vars = datasets.expander.get_expanded_vars_per_str_var(request.algorithm, request.input_dependent)
    hyperparams = datasets.expander.get_expanded_hyperparams(request.algorithm, request.input_dependent)
    inputs_and_hyperparams = datasets.expander.get_expanded_ml_input_vars(request.algorithm, request.input_dependent)
    var_type = datasets.expander.get_expanded_var_type(request.algorithm, request.input_dependent)
    var_bounds = dict({var : var_bounds[var] for var in var_bounds if var not in str_vars},
            **{category : {'lb' : 0, 'ub' : 1} for var, categories in str_vars.items() for category in categories})

    # Retrieve variable types, assuming that price is always a float
    cplex_type = {'bin' : mdl.binary_vartype, 'int' : mdl.integer_vartype, 'float' : mdl.continuous_vartype}
    var_type['price'] = 'float'
    var_type = {var : cplex_type[var_type[var]] for var in var_type.keys()}

    ####### VARIABLES #######
    # A binary variable for each hw, specifying whether this hw is selected or not
    for hw in hws:
        mdl.binary_var(name = f"b_{hw}")

    ml_var = {}

    # A variable for each hyperparameter, whose type matches the hyperparameter's type
    # If the hyperparameter is non-continuous, it also requires an auxiliary continuous variable and 
    # an integrality constraint: the auxiliary variable is used as input to the predictive models (emllib 
    # accepts only continuous variables), the integrality (equality) constraint is used to convert the 
    # auxiliary variable back into the binary/integer one
    # NEW: now handles both input variables (input-dependent case) and hyperparameters
    for var in inputs_and_hyperparams:
    #for hyperparam in hyperparams:
        mdl.var(name = var, 
                vartype = var_type[var],
                lb = var_bounds[var]['lb'],
                ub = var_bounds[var]['ub'])
        ml_var[var] = var
        if var_type[var] != mdl.continuous_vartype:
            mdl.var(name = f"auxiliary_{var}", 
                    vartype = mdl.continuous_vartype,
                    lb = var_bounds[var]['lb'],
                    ub = var_bounds[var]['ub'])
            mdl.add_constraint(mdl.get_var_by_name(var) == mdl.get_var_by_name(f"auxiliary_{var}"), ctname = f"{var}_integrality_constraint")
            ml_var[var] = f'auxiliary_{var}'

    # A variable for each target and hw, whose type matches the target's type. 
    # Also in this case, if the target is non-continuous, it requires auxiliary variables and constraints
    for target in targets:
        for hw in hws:
            mdl.var(name = f"{hw}_{target}", 
                    vartype = var_type[target],
                    lb = var_bounds[target]['lb'],
                    ub = var_bounds[target]['ub'])
            ml_var[f'{hw}_{target}'] = f'{hw}_{target}'
            if var_type[target] != mdl.continuous_vartype:
                mdl.var(name = f"auxiliary_{hw}_{target}", 
                    vartype = mdl.continuous_vartype,
                    lb = var_bounds[target]['lb'],
                    ub = var_bounds[target]['ub'])
                mdl.add_constraint(mdl.get_var_by_name(f'{hw}_{target}') == mdl.get_var_by_name(f"auxiliary_{hw}_{target}"), ctname = f"{hw}_{target}_integrality_constraint")
                ml_var[f'{hw}_{target}'] = f'auxiliary_{hw}_{target}'

    ####### CONSTRAINTS ######
    # Constraints on input values
    if request.input_dependent:
        inputs = request.inputs.get_inputs()
        inputs_types = {var:type for var,type in db.get_type_per_var(request.algorithm, request.input_dependent).items()
                        if var in inputs.keys()}
        for input_var, type in inputs_types.items():
            if type == 'str':
                enc_categories = datasets.expander.get_encoded_selection(request.algorithm, input_var, inputs[input_var], request.input_dependent)
                for enc_input, enc_value in enc_categories.items():
                    mdl.add_constraint(mdl.get_var_by_name(enc_input) == enc_value, ctname = f"auxiliary_{enc_input}")
            else:
                mdl.add_constraint(mdl.get_var_by_name(input_var) == inputs[input_var], ctname = f"auxiliary_{input_var}")


    # HW Selection Constraint, enabling the selection of a single hw platform
    mdl.add_constraint(mdl.sum(mdl.get_var_by_name(f"b_{hw}") for hw in hws) == 1, ctname = "hw_selection")

    # Category Selection Constraints, enabling the selection of a single category for each categorical variable
    for var in str_vars:
        mdl.add_constraint(mdl.sum(mdl.get_var_by_name(category) for category in str_vars[var]) == 1, ctname = f"{var}_category_selection")

    # Empirical Constraints: embed the predictive models into the system (through emllib)
    for target in targets:
        # target price is not predicted, but indicated by the hw provider: it does not require any
        # dedicated predictive model
        if target == "price": 
            continue
        # time and memory depend on both the hw and the algorithm configuration: each of them requires three 
        # dedicated predictive models
        for hw in hws:
            model = models.get_model(request.algorithm, hw, target, request.input_dependent)
            if model.tree_.node_count <= 1:
                continue
            model = read_sklearn_tree(model)
            #for i, hyperparam in enumerate(hyperparams):
            #for i, var in enumerate(inputs_and_hyperparams):
            for idx in model.attributes_ub.keys():
                var = inputs_and_hyperparams[idx]
                model.update_lb(idx, var_bounds[var]['lb'])
                model.update_ub(idx, var_bounds[var]['ub'])

            embed.encode_backward_implications(
                    bkd = bkd, mdl = mdl,
                    tree = model, 
                    tree_in = [mdl.get_var_by_name(ml_var[var]) for var in inputs_and_hyperparams],
                    tree_out = mdl.get_var_by_name(ml_var[f"{hw}_{target}"]),
                    name = f"DT_{hw}_{target}")

    
    # Handling non-estimated target (price) and robustness coefficients: 
    # 1.Equality constraints, fixing each price variable hw_price to the usage price of the corresponding hw,
    # as required by the hw provider
    if 'price' in targets:
        for hw in hws: 
            mdl.add_constraint(mdl.get_var_by_name(f"{hw}_price") == request.hws_prices.get_prices_per_hw()[hw], ctname = f"{hw}_price")
 
    # 2. If no robustness is required, fix all coefficients to 0 
    if robust_coeff is None:
        robust_coeff = {(hw, target) : 0
                        for hw in hws
                        for target in request.user_constraints.get_constraints()}
    
    # User-defined constraints, bounding the performance of the algorithm, as required by the user
    for target in request.user_constraints.get_constraints():
        for hw in hws:
            if request.user_constraints.get_constraints()[target][0] == "leq":
                mdl.add_indicator(mdl.get_var_by_name(f"b_{hw}"), 
                        mdl.get_var_by_name(f"{hw}_{target}") <= request.user_constraints.get_constraints()[target][1] - robust_coeff[(hw,target)], 1, name = f"user_constraint_{target}_{hw}")
            elif request.user_constraints.get_constraints()[target][0] == "geq":
                mdl.add_indicator(mdl.get_var_by_name(f"b_{hw}"), 
                        mdl.get_var_by_name(f"{hw}_{target}") >= request.user_constraints.get_constraints()[target][1] + robust_coeff[(hw,target)], 1, name = f"user_constraint_{target}_{hw}")
            elif request.user_constraints.get_constraints()[target][0] == "eq":
                mdl.add_indicator(mdl.get_var_by_name(f"b_{hw}"), 
                        mdl.get_var_by_name(f"{hw}_{target}") >= request.user_constraints.get_constraints()[target][1] - robust_coeff[(hw, target)], 1, name = f"user_constraint_{target}_{hw}_1")
                mdl.add_indicator(mdl.get_var_by_name(f"b_{hw}"), 
                        mdl.get_var_by_name(f"{hw}_{target}") <= request.user_constraints.get_constraints()[target][1] + robust_coeff[(hw, target)], 1, name = f"user_constraint_{target}_{hw}_2")

    ##### OBJECTIVE #####
    if request.opt_type == "min":
        mdl.minimize(mdl.sum( mdl.get_var_by_name(f"{hw}_{request.target}") * mdl.get_var_by_name(f"b_{hw}") for hw in hws))
    else: 
        mdl.maximize(mdl.sum(mdl.get_var_by_name(f"{hw}_{request.target}") * mdl.get_var_by_name(f"b_{hw}") for hw in hws))

         
    ##### SOLVE #####
    sol = mdl.solve()
    
    solution = None
    if sol:
        for hw in hws:
            if round(sol[f'b_{hw}']) == 1:
                chosen_hw = hw
                break
        targets_values = {target: round(sol[f"{chosen_hw}_{target}"]) if var_type[target] != mdl.continuous_vartype else sol[f"{chosen_hw}_{target}"] for target in targets}
        hyperparams_values = {hyperparam: round(sol[hyperparam]) if var_type[hyperparam] != mdl.continuous_vartype else sol[hyperparam] for hyperparam in hyperparams}
        
        # Decode one-hot hyperparameters
        for var in set(str_vars.keys()).intersection(db.get_hyperparams(request.algorithm, request.input_dependent)):
            chosen_category = {var : category.split(var + '_')[1] for category in str_vars[var] if hyperparams_values[category] == 1}
            hyperparams_values = dict({hyperparam : value for hyperparam, value in hyperparams_values.items() if hyperparam not in str_vars[var]},
            **chosen_category)

        #solution = {'chosen_hw': chosen_hw, 'hyperparams': hyperparams_values, 'targets': targets_values}
        solution = OptimizationSolution(chosen_hw, hyperparams_values, targets_values)

    return solution
