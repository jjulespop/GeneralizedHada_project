import docplex
from eml.backend import cplex_backend
from eml.tree.reader.sklearn_reader import read_sklearn_tree
from eml.tree import embed 
from docplex.mp.model_reader import ModelReader
from configdb import ConfigDB
from solution import OptimizationSolution
#response =

def HADA(db: ConfigDB,
        request,
        models,
        var_bounds,
        robust_coeff):
    '''
    TODO: handle integer and continous vars both for targets and hyperparams (based on the declared "type")
    TODO: hyperparams are not necessarily called "var_{i}" anymore
    Implement HADA:
        1. Declare variables and basic constraints
        2. Embed predictive models 
        3. Declare user-defined constraints and objective 
        4. Solve the model and output an optimal matching (hw-platform, alg-configuration)

    PARAMETERS
    ---------
    xxx [yyy] : a transprecision computing algorithm {saxpy, convolution, correlation, fwt}
    xxx [yyy]: type {min, max} and target

    RETURN
    ------
    sol [dict]: optimal solution found
    mdl [docplex.mp.model.Model]: final optimization model
    '''

    bkd = cplex_backend.CplexBackend()
    mdl = docplex.mp.model.Model("HADA")

    hws = db.get_hws(request.algorithm)
    targets = db.get_targets(request.algorithm)
    hyperparams = db.get_hyperparams(request.algorithm)
    n_hyperparams = len(hyperparams)
    #n_hyperparams = len(db.get_hyperparams(request.algorithm))

    ####### MODEL #######
    #ALL_VARS = [f"b_{hw}" for hw in db.get_hws(request.algorithm)] + \
    #           [f"y_{hw}_{target}" for hw in hws for target in targets + ['price']] + \
    #           [f"var_{hyperparam}" for hyperparam in hyperparams]
    #           #[f"var_{i}" for i in range(n_hyperparams)]
    DECLARED_VARS = []

    ####### VARIABLES #######
    # A binary variable for each hw, specifying whether this hw is selected or not
    for hw in hws:
        mdl.binary_var(name = f"b_{hw}")
        DECLARED_VARS = DECLARED_VARS + [f"b_{hw}"]

    # Continuous variables representing the target values 
    # TODO: should we represent here all continous vars (either hyperparams or targets)?
    # TODO: should we represent here all continous vars (either hyperparams or targets)?
    # TODO: should we represent here all continous vars (either hyperparams or targets)?
    for target in set(list(request.user_constraints.get_constraints()) + [request.target, 'price']):
        for hw in hws:
            mdl.continuous_var(name = f"y_{hw}_{target}", 
                               lb = var_bounds[target]['lb'],
                               ub = var_bounds[target]['ub'])
            DECLARED_VARS = DECLARED_VARS + [f"y_{hw}_{target}"]

    # An integer variable and an auxiliary continuous variable for each integer parameter of the algorithm, 
    # representing the value assigned to this parameter: the auxiliary variables are used as input to the 
    # predictive models (emllib accepts solely continuous variables), then converted into integer variables
    # through an equality constraint
    # TODO: should we represent here all integer vars (either hyperparams or targets)?
    # TODO: hyperparams can have names different than "var_{i}" -> map them somehow
    for hyperparam in hyperparams:
        hyperparam_lb = var_bounds[hyperparam]['lb']
        hyperparam_ub = var_bounds[hyperparam]['ub']
        mdl.integer_var(name = f"var_{hyperparam}", 
                        lb = hyperparam_lb,
                        ub = hyperparam_ub) 
        mdl.continuous_var(name = f"auxiliary_var_{hyperparam}", 
                           lb = hyperparam_lb,
                           ub = hyperparam_ub)
        DECLARED_VARS = DECLARED_VARS + [f"var_{hyperparam}"]

    ####### CONSTRAINTS ######
    # HW Selection Constraint, enabling the selection of a single hw platform
    mdl.add_constraint(mdl.sum(mdl.get_var_by_name(f"b_{hw}") for hw in hws) == 1,
                       ctname = "hw_selection")

    # Integrality Constraints, enabling the conversion of the auxiliary variables from continuous to integer
    for hyperparam in hyperparams:
        mdl.add_constraint(mdl.get_var_by_name(f"var_{hyperparam}") == mdl.get_var_by_name(f"auxiliary_var_{hyperparam}"), 
                ctname = f"var_{hyperparam}_integrality_constraint")
    
    # Empirical Constraints: embed the predictive models into the system (through emllib)
    for target in set(list(request.user_constraints.get_constraints()) + [request.target]):
        # target price is not predicted, but indicated by the hw provider: it does not require any
        # dedicated predictive model
        if target == "price": 
            continue
        # time and memory depend on both the hw and the algorithm configuration: each of them requires three 
        # dedicated predictive models
        for hw in hws:
            model = models.get_model(request.algorithm, hw, target)
            model = read_sklearn_tree(model)
            for i, hyperparam in enumerate(hyperparams):
                model.update_lb(i, var_bounds[hyperparam]['lb'])
                model.update_ub(i, var_bounds[hyperparam]['ub'])
            embed.encode_backward_implications(
                    bkd = bkd, mdl = mdl,
                    tree = model, 
                    tree_in = [mdl.get_var_by_name(f"auxiliary_var_{hyperparam}") 
                               for i in range(n_hyperparams)],
                    tree_out = mdl.get_var_by_name(f"y_{hw}_{target}"),
                    name = f"DT_{hw}_{target}")
    
    # Handling non-estimated target (price) and robustness coefficients: 
    # 1.Equality constraints, fixing each price variable y_hw_price to the usage price of the corresponding hw,
    # as required by the hw provider
    for target in set(list(request.user_constraints.get_constraints()) + [request.target, 'price']):
        for hw in hws: 
            mdl.add_constraint(mdl.get_var_by_name(f"y_{hw}_price") == request.hws_prices.get_prices_per_hw()[hw],
                               ctname = f"{hw}_price")

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
                        mdl.get_var_by_name(f"y_{hw}_{target}") <= request.user_constraints.get_constraints()[target][1] - robust_coeff[(hw,target)], 1, name = f"user_constraint_{target}_{hw}")
            elif request.user_constraints.get_constraints()[target][0] == "geq":
                mdl.add_indicator(mdl.get_var_by_name(f"b_{hw}"), 
                        mdl.get_var_by_name(f"y_{hw}_{target}") >= request.user_constraints.get_constraints()[target][1] + robust_coeff[(hw,target)], 1, name = f"user_constraint_{target}_{hw}")
            elif request.user_constraints.get_constraints()[target][0] == "eq":
                mdl.add_indicator(mdl.get_var_by_name(f"b_{hw}"), 
                        mdl.get_var_by_name(f"y_{hw}_{target}") >= request.user_constraints.get_constraints()[target][1] - robust_coeff[(hw, target)], 1, name = f"user_constraint_{target}_{hw}_1")
                mdl.add_indicator(mdl.get_var_by_name(f"b_{hw}"), 
                        mdl.get_var_by_name(f"y_{hw}_{target}") <= request.user_constraints.get_constraints()[target][1] + robust_coeff[(hw, target)], 1, name = f"user_constraint_{target}_{hw}_2")

    ##### OBJECTIVE #####
    if request.opt_type == "min":
        mdl.minimize(mdl.sum( mdl.get_var_by_name(f"y_{hw}_{request.target}") * mdl.get_var_by_name(f"b_{hw}") for hw in hws))
    else: 
        mdl.maximize(mdl.sum(mdl.get_var_by_name(f"y_{hw}_{request.target}") * mdl.get_var_by_name(f"b_{hw}") for hw in hws))

        
    ##### SOLVE #####
    sol = mdl.solve()
    
    solution = None
    if sol:
        hyperparams_values = {hyperparam: sol[f"var_{hyperparam}"] for hyperparam in hyperparams}
        for hw in hws:
            if sol[f'b_{hw}'] == 1:
                chosen_hw = hw
                break
        targets_values = {target:sol[f"y_{chosen_hw}_{target}"] for target in targets + ['price']} 

        #solution = {'chosen_hw': chosen_hw, 'hyperparams': hyperparams_values, 'targets': targets_values}
        solution = OptimizationSolution(chosen_hw, hyperparams_values, targets_values)

    return solution, mdl

    #solution = {}

    #hw_vars = {}
    #hyperparam_vars = {}
    #target_vars_per_hw = defaultdict(dict)

    ####### MODEL #######
    #hw_sol = {hw:sol[f"b_{hw}"] for hw in db.get_hws(request.algorithm)}
    #hyparparams_sol = {hyperparam: sol[f"var_{hyperparam}"] for hyperparam in hyperparams}
    #targets_sol_per_hw = {hw:{target:sol[f"y_{hw}_{target}"] for target in targets} for hw in hws}
    #for var in DECLARED_VARS:
    #    if var.startswith('b_'):
    #        clean_name = var[2:]
    #        hw_vars[clean_name] = sol[var]
    #    elif var.startswith('var_'):
    #        clean_name = var[4:]
    #        hyperparam_vars[clean_name] = sol[var]
    #    elif var.startswith('y_'):
    #        clean_name = var[4:]
    #        hyperparam_vars[clean_name] = sol[var]
    #        elif var.startswith('var_')
    #for var in variables:
    #    if var.startswith('b_') and variables[var] == 1:
    #        solution['hw'] = var[2:]
