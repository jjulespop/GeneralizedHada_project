import docplex
from eml.backend import cplex_backend
from eml.tree.reader.sklearn_reader import read_sklearn_tree
from eml.tree import embed 
from docplex.mp.model_reader import ModelReader
from core.configdb import ConfigDB
from core.optimization_request import OptimizationSolution
from core.logic_models import get_linear_expression
import docplex.mp.conflict_refiner as cr

def HADA(db: ConfigDB,
         request,
         logic_models,
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
    xxx [yyy] : a transprecision computing algorithm {saxpy, convolution, correlation, fwt}
    xxx [yyy]: type {min, max} and target

    RETURN
    ------
    sol [dict]: optimal solution found
    mdl [docplex.mp.model.Model]: final optimization model
    '''

    ####### MODEL #######
    #bkd = cplex_backend.CplexBackend()
    mdl = docplex.mp.model.Model("HADA")
    #mdl.parameters.mip.tolerances.integrality = 0.0

    hws = db.get_hws(request.algorithm)
    targets = set(list(request.user_constraints.get_constraints().keys()) + [request.target])
    hyperparams = db.get_hyperparams(request.algorithm)
    input_vars = db.get_input_vars(request.algorithm)

    # Retrieve variable types, assuming that price is always a float
    cplex_type = {'bin' : mdl.binary_vartype, 'int' : mdl.integer_vartype, 'float' : mdl.continuous_vartype}
    var_type = db.get_type_per_var(request.algorithm)
    var_type['price'] = 'float'
    var_type = {var : cplex_type[var_type[var]] for var in var_type.keys()}
    for var, bounds in var_bounds.items():
        if bounds['ub'] == float('inf'):
            var_bounds[var]['ub'] = mdl.infinity
        if bounds["lb"] == float('-inf'):
            var_bounds[var]["lb"] = -mdl.infinity
    ####### VARIABLES #######
    # A binary variable for each hw, specifying whether this hw is selected or not
    for hw in hws:
        mdl.binary_var(name = f"b_{hw}")


    # A variable for each hyperparameter, whose type matches the hyperparameter's type
    for hyperparam in hyperparams:
        mdl.var(name = hyperparam, 
                vartype = var_type[hyperparam],
                lb = var_bounds[hyperparam]['lb'],
                ub = var_bounds[hyperparam]['ub'])

    for input_var in input_vars:
        mdl.var(name = input_var,
                vartype = var_type[input_var],
                lb = var_bounds[input_var]['lb'],
                ub = var_bounds[input_var]['ub'])



    #constraints for input variables
    for input_var in request.inputs.get_inputs().keys():
        mdl.add_constraint(mdl.get_var_by_name(input_var) == request.inputs.get_inputs()[input_var], ctname = f"{input_var}_input_variable_constraint")

    # A variable for each target and hw, whose type matches the target's type.
    for target in targets:
        for hw in hws:
            mdl.var(name = f"{hw}_{target}", 
                    vartype = var_type[target],
                    lb = var_bounds[target]['lb'],
                    ub = var_bounds[target]['ub'])


    ####### CONSTRAINTS ######
    # HW Selection Constraint, enabling the selection of a single hw platform
    mdl.add_constraint(mdl.sum(mdl.get_var_by_name(f"b_{hw}") for hw in hws) == 1, ctname = "hw_selection")

    # Empirical Constraints: embed the predictive models into the system (through emllib)
    for target in targets:
        # target price is not predicted, but indicated by the hw provider: it does not require any
        # dedicated predictive model
        if target == "price": 
            continue
        # time and memory depend on both the hw and the algorithm configuration: each of them requires three 
        # dedicated predictive models
        for hw in hws:
            rules = logic_models.get_rules(request.algorithm, hw, target)
            #avoid intersections
            rules = logic_models.reduce_domain(rules)
            then_vars = []
            for i, rule in enumerate(rules):#add the logic logic_rules to the model
                if_con = rule["if"]
                then_var_name = f'var_then_{hw}_{target}_{i}'
                then_var = mdl.binary_var(then_var_name)
                then_vars.append(then_var)
                for j, var in enumerate(if_con["var"]):
                    #if part of the rule
                    if if_con["type"][j] == "range":
                        mdl.add_indicator(then_var, mdl.get_var_by_name(var) <= if_con["value"][j][1], name=f'ub_{var}_rule_{i}_{j}_{target}_{hw}')
                        mdl.add_indicator(then_var, mdl.get_var_by_name(var) >= if_con["value"][j][0], name=f'lb_{var}_rule_{i}_{j}_{target}_{hw}')
                    if if_con["type"][j] == ">=" or  if_con["type"][j] == ">":
                        mdl.add_indicator(then_var, mdl.get_var_by_name(var) >= if_con["value"][j], name=f'lb_{var}_rule_{i}_{j}_{target}_{hw}')
                    if if_con["type"][j] == "<=" or if_con["type"][j] == "<":
                        mdl.add_indicator(then_var, mdl.get_var_by_name(var) <= if_con["value"][j], name=f'ub_{var}_rule_{i}_{j}_{target}_{hw}')
                #then part of the rule
                then_con = rule["then"]
                for j, var in enumerate(then_con["var"]):
                    if then_con["type"][j] == "==":#there is only one
                        expression = then_con["value"][j]
                        mdl.add_indicator(then_var, mdl.get_var_by_name(f'{hw}_{var}') == eval(get_linear_expression(expression)), name=f'expression_{i}_{j}_{target}_{hw}')

            mdl.add_constraint(mdl.sum(then_vars) == 1, ctname=f"one_rule_true_{target}_{hw}")#only one rule is true
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
    mdl.export_as_lp('model.lp') #export the model
    sol = mdl.solve(log_output=False)
    #print(mdl.solve_details)
    #cref = cr.ConflictRefiner()
    #cref.refine_conflict(mdl, display=True)
    solution = None
    if sol:
        for hw in hws:
            if round(sol[f'b_{hw}']) == 1:
                chosen_hw = hw
                break
        targets_values = {target: round(sol[f"{chosen_hw}_{target}"]) if var_type[target] != mdl.continuous_vartype else sol[f"{chosen_hw}_{target}"] for target in targets}
        hyperparams_values = {hyperparam: round(sol[hyperparam]) if var_type[hyperparam] != mdl.continuous_vartype else sol[hyperparam] for hyperparam in hyperparams}
        #solution = {'chosen_hw': chosen_hw, 'hyperparams': hyperparams_values, 'targets': targets_values}
        solution = OptimizationSolution(chosen_hw, hyperparams_values, targets_values, mdl.number_of_variables, mdl.number_of_constraints)
    else:
        solution = OptimizationSolution(num_variables=mdl.number_of_variables, num_constraints=mdl.number_of_constraints)
    return solution
