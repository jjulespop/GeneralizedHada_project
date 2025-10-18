import docplex
import numpy as np
from eml.backend import cplex_backend
from eml.tree.reader.sklearn_reader import read_sklearn_tree
from eml.tree import embed 
from docplex.mp.model_reader import ModelReader
from hada.core.config.configdb import ConfigDB
from hada.core.models.logic_models import LogicModels
from hada.core.optimization.optimization_request import OptimizationRequest
from hada.core.optimization.optimization_solution import OptimizationSolution
from hada.core.models.logic_models import get_linear_expression
import docplex.mp.conflict_refiner as cr



def add_rule_constraints(mdl, hw: str, target: str, rule_index: int, rules: dict[str, list[dict]]) -> list:
    """Add constraints for a specific (hw, target, rule) and return them."""
    
    rule = rules[target][rule_index]
    if_con, then_con = rule["if"], rule["then"]
    constraints = []

    # "if" conditions
    for j, var in enumerate(if_con["var"]):
        type = if_con["type"][j]
        value = if_con["value"][j]
        var_obj = mdl.get_var_by_name(var)

        if type == "range":
            con0 = mdl.add_constraint(var_obj >= value[0],
                                    ctname=f'lb_{var}_rule_{rule_index}_{j}_{target}_{hw}')
            con1 = mdl.add_constraint(var_obj <= value[1],
                                    ctname=f'ub_{var}_rule_{rule_index}_{j}_{target}_{hw}')
            constraints.append(con0)
            constraints.append(con1)
        
        elif type in [">=", ">"]:
            con = mdl.add_constraint(var_obj >= value,
                                    ctname=f'lb_{var}_rule_{rule_index}_{j}_{target}_{hw}')
            constraints.append(con)
        
        elif type in ["<=", "<"]:
            con = mdl.add_constraint(var_obj <= value,
                                    ctname=f'ub_{var}_rule_{rule_index}_{j}_{target}_{hw}')
            constraints.append(con)

    # "then" expressions
    for j, var in enumerate(then_con["var"]):
        
        if then_con["type"][j] == "==":
            expression = then_con["value"][j]
            con = mdl.add_constraint(mdl.get_var_by_name(f'{hw}_{var}') == eval(get_linear_expression(expression)),
                                    ctname=f'expression_{rule_index}_{j}_{target}_{hw}')
            constraints.append(con)

    return constraints



def HADA(db: ConfigDB,
         request: OptimizationRequest,
         logic_models: LogicModels,
         var_bounds: dict,
         robust_coeff: dict | None):
    """
    Implements the HADA optimization algorithm, iterative version.

    Steps:
        1. Declare variables and basic constraints.
        2. Embed predictive models.
        3. Apply user-defined constraints and objective.
        4. Solve the optimization problem and output optimal solution (hw-platform, alg-configuration).

    Args:
        db (ConfigDB): configuration database instance.
        request: OptimizationRequest instance.
        logic_models: rules extractor.
        var_bounds (dict): bounds for all variables.
        robust_coeff (dict | None): optional robustness coefficients.

    Returns:
        OptimizationSolution: encapsulates chosen hardware, hyperparameters, target values, etc.
    """

    # load HADA
    bkd = cplex_backend.CplexBackend()
    mdl = docplex.mp.model.Model("HADA")

    ### VARIABLES ###
    hws = db.get_hws(request.algorithm)
    #targets = set(list(request.user_constraints.get_constraints().keys()) + [request.target])
    targets = list(set(list(request.user_constraints.get_constraints().keys()) + [request.target]))
    list.sort(targets)
    hyperparams = db.get_hyperparams(request.algorithm)
    input_vars = db.get_input_vars(request.algorithm)

    # map variable types for CPLEX
    cplex_type = {'bin' : mdl.binary_vartype, 'int' : mdl.integer_vartype, 'float' : mdl.continuous_vartype}
    var_type = db.get_type_per_var(request.algorithm)
    var_type['price'] = 'float'
    var_type = {var : cplex_type[var_type[var]] for var in var_type.keys()}
    
    # fix infinite bounds for CPLEX
    for var, bounds in var_bounds.items():
        if bounds['ub'] == float('inf'):
            var_bounds[var]['ub'] = mdl.infinity
        if bounds["lb"] == float('-inf'):
            var_bounds[var]["lb"] = -mdl.infinity
    
    # hardware selection binary variables
    for hw in hws:
        mdl.binary_var(name = f"b_{hw}")

    # hyperparameter and input variables
    for hyperparam in hyperparams:
        mdl.var(
            name = hyperparam, 
            vartype = var_type[hyperparam],
            lb = var_bounds[hyperparam]['lb'],
            ub = var_bounds[hyperparam]['ub']
        )

    for input_var in input_vars:
        mdl.var(
            name = input_var,
            vartype = var_type[input_var],
            lb = var_bounds[input_var]['lb'],
            ub = var_bounds[input_var]['ub']
        )

    # # constraints for input variables
    if request.is_input_dependent():
        for input_var in request.inputs.get_inputs().keys():
            mdl.add_constraint(mdl.get_var_by_name(input_var) == request.inputs.get_inputs()[input_var], ctname = f"{input_var}_input_variable_constraint")

    # target variables for hardware
    for target in targets:
        for hw in hws:
            mdl.var(
                name = f"{hw}_{target}", 
                vartype = var_type[target],
                lb = var_bounds[target]['lb'],
                ub = var_bounds[target]['ub']
            )


    ### CONSTRAINTS ###
    # HW Selection Constraint, enabling the selection of a single hw platform
    mdl.add_constraint(mdl.sum(mdl.get_var_by_name(f"b_{hw}") for hw in hws) == 1, ctname = "hw_selection")

    # Handling non-estimated target (price) and robustness coefficients: 
    # 1. Equality constraints, fixing each price variable hw_price to the usage price of the corresponding hw, as required by the hw provider
    if 'price' in targets:
        for hw in hws: 
            mdl.add_constraint(
                mdl.get_var_by_name(f"{hw}_price") == request.hws_prices.get_prices_per_hw()[hw], 
                ctname = f"{hw}_price"
            )

    # 2. If no robustness is required, fix all coefficients to 0 
    if robust_coeff is None:
        robust_coeff = {
            (hw, target) : 0
            for hw in hws
            for target in request.user_constraints.get_constraints()
        }


    ### USER CONSTRAINTS ###
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


    ### OBJECTIVE ###
    objective_expr = mdl.sum( mdl.get_var_by_name(f"{hw}_{request.target}") * mdl.get_var_by_name(f"b_{hw}") for hw in hws)
    if request.objective == "min":
        mdl.minimize(objective_expr)
    else: 
        mdl.maximize(objective_expr)


    ### ITERATION ###
    solution = None
    logic_constraints = {}
    
    for hw in hws:

        rules = {target: logic_models.get_rules(request.algorithm, hw, target) for target in targets}
        rule_counts = [len(rules[target]) for target in targets]
        rule_indices = [0] * len(targets)
        changed_flags = [False] * len(targets)

        # initialize first set of constraints
        for target in targets:
            logic_constraints[f'{hw}_{target}'] = add_rule_constraints(mdl, hw, target, 0, rules)

        # try to solve iteratively by cycling through rule combinations
        while_condition = True
        n_variables, n_constraints = [], []
        
        # search a solution with different rules until it is found
        while while_condition:

            # try to solve
            sol = mdl.solve(log_output=False)
            n_variables.append(mdl.number_of_variables)
            n_constraints.append(mdl.number_of_constraints)

            if sol:
                while_condition = False
                break

            # update rule indices
            rule_indices[0] += 1
            changed_flags[0] = True

            # setting things for next iteration            
            for k, target in enumerate(targets):
            
                if rule_indices[k] == rule_counts[k]:
            
                    if k == len(targets) - 1:
                        # no rule combination gives a feasible solution
                        while_condition = False 
                        break
                    
                    # change the ruke relative to next target if we got to the last
                    rule_indices[k] =  0
                    changed_flags[k] = True
                    rule_indices[k + 1] += 1
                    changed_flags[k + 1] = True
                
                if changed_flags[k]:
                    # remove old constraints
                    mdl.remove(logic_constraints[f'{hw}_{target}'])

                    # add new constraints
                    logic_constraints[f'{hw}_{target}'] = add_rule_constraints(mdl, hw, target, rule_indices[k], rules)

                    changed_flags[k] = False

        # clean up constraints before moving to next hardware item
        for target in targets:
            mdl.remove(logic_constraints[f'{hw}_{target}'])


    ### SOLVE ###
    # export the model
    # mdl.export_as_lp('model.lp') 

    if sol:
        for hw in hws:
            if round(sol[f'b_{hw}']) == 1:
                chosen_hw = hw
                break
        
        targets_values = {
            target: round(sol[f"{chosen_hw}_{target}"]) 
            if var_type[target] != mdl.continuous_vartype 
            else sol[f"{chosen_hw}_{target}"] 
            for target in targets
        }
        
        hyperparams_values = {
            hyperparam: round(sol[hyperparam]) 
            if var_type[hyperparam] != mdl.continuous_vartype 
            else sol[hyperparam] 
            for hyperparam in hyperparams
        
        }
        # solution = {'chosen_hw': chosen_hw, 'hyperparams': hyperparams_values, 'targets': targets_values}
        solution = OptimizationSolution(chosen_hw, hyperparams_values, targets_values, np.average(n_variables), np.average(n_constraints))
    
    else:
        solution = OptimizationSolution(num_variables=np.average(n_variables), num_constraints=np.average(n_constraints))
    
    return solution
