"""
Class that handles operations that have to be carried out on logic rules.
"""

import ast
import os
import re
import copy
import numpy as np
import pandas as pd


class LogicModels():
    """Handles all operations related to logic-based rule models."""


    VALID_RULE_NAMES = {'GridREx', 'GridEx', 'CReEPy', 'CART'}


    def __init__(self, db, rules_path: str, rules_name: str):
        """Handles all operations on the Logic Model.

        Args:
            db (ConfigDB): ConfigDB instance.
            rules_path (str): local path where the logic_rules are stored.
            name (str): name of the extractor
        """

        if rules_name not in self.VALID_RULE_NAMES:
            raise AttributeError(f'Wrong rules name {rules_name}. Options: GridREx,  GridEx,  CReEPy,  CART.')
        
        self.db = db
        self.rules_path = rules_path
        self.rules_name = rules_name


    def __get_rules_path(self, algorithm: str, hw: str, target: str) -> str:
        """
        Construct the file path to a specific rule file.

        Args:
            algorithm (str): algorithm name.
            hw (str): Hhardware identifier.
            target (str): target metric.

        Returns:
            str: full path to the rule file.
        """
         
        filename = f"{algorithm}_{hw}_{target}.txt"
        return os.path.join(self.rules_path, self.rules_name, filename)


    def get_rules(self, algorithm: str, hw: str, target: str) -> list[dict]:
        """
        Retrieve and parse logic rules for GridEx, GridREx, CReEPy, and CART.

        Args:
            algorithm (str): algorithm identifier.
            hw (str): hardware platform identifier.
            target (str): target variable identifier.

        Raises:
            FileNotFoundError: if the rules file does not exist.
            ValueError: if the file contains invalid or unparsable content.

        Returns:
            logic_rules (list[dict]): list of parsed logic rules, each of the form:
                [{'if': {'var': [...], 'type': ['range'], value:[[lb, up], ...]} ,  'then':{'var': [...], 'type': ['=='], value:[expr, ...]} }, ...]
        """

        rules_path = self.__get_rules_path(algorithm, hw, target)

        if not os.path.exists(rules_path):
            raise FileNotFoundError(f"Logic rules for ({algorithm}, {hw}, {target}) not found at {rules_path}")
        
        with open(rules_path, "r") as file:
            lines = file.readlines()
        
        rules=[]
        hyperparam = 'nScenarios' if algorithm == 'anticipate' else 'nTraces'

        for index, line in enumerate(lines):

            # even lines: rule head (THEN clause)
            if index % 2 == 0:
                then_constraint = {"var": [], "value": [], "type": ["=="]}
                
                if re.search(r'\d', line):
                    try:
                        _, expression = line.split(f"{hyperparam},")
                        expression, _ = expression.split(')')
                        then_constraint["var"].append(target)
                        then_constraint["value"].append(expression.strip())
                    except ValueError:
                        raise ValueError(f"Malformed THEN clause in line {index + 1}: {line}")

            # odd lines: rule body (IF clause)
            else:
                if_constraint = {"var": [], "value": [], "type": []}

                # case: equality rule, e.g., "if X is Y"
                if " is " in line:
                    then_constraint = {"var": [], "value": [], "type": ["=="]}
                    _, expr = line.split(f" {target} is ")
                    then_constraint["var"].append(target)
                    then_constraint["value"].append(expr.strip()[0:-1])
                
                # case: intervals, e.g., "X in [a,b]"
                if "[" in line:
                    parts = re.split('][.,]', line)

                    for part in parts:

                        if not part.strip():
                            continue
                        
                        if ' in ' not in part:
                            continue
                        var, interval_str = part.strip().split(' in ')
                        
                        try:
                            interval = ast.literal_eval(interval_str + "]")
                        except (SyntaxError, ValueError):
                            raise ValueError(f"Invalid interval syntax for variable '{var}': {interval_str}")
                        
                        if_constraint["var"].append(var.strip())
                        if_constraint["value"].append(interval)
                        if_constraint["type"].append("range")
                
                # case: numeric comparisons, e.g., "X <= 5, Y > 10"
                else:
                    parts = re.split(',', line)

                    for i, part in enumerate(parts):

                        if i == len(parts) - 1:
                            part = part[0: -2]
                        
                        if len(part) < 2:
                            continue
                        
                        if '=<' in part:
                            op = '<='
                        
                        else:
                            if '=>' in part:
                                op = '>='
                            
                            else:
                                if '<' in part:
                                    op = '<'
                                
                                else:
                                    if '>' in part:
                                        op = '>'

                        
                        var, val = re.split('[=]*[<>]', part)
                        if_constraint["var"].append(var.strip())
                        if_constraint["value"].append(eval(val.strip()))
                        if_constraint["type"].append(op)

                rule = {"if": if_constraint, "then": then_constraint}
                rules.append(rule)

        # handle rule with no body
        if index % 2 == 0:
            rule = {"if": {"var": [], "value": [], "type": []}, "then": then_constraint}
            rules.append(rule)
        
        return rules


    def reduce_domain(self, rules: list[dict]) -> list[dict]:
        """
        Reduce the domain of each logic rule to avoid intersections.
        Depending on the rule extractor (CReEPy, CART, GridREx, GridEx), this function modifies the rules' input variable bounds to produce non-overlapping domains.

        Args:
            rules (list[dict]): list of logic rules.

        Returns:
            new_rules (list[dict]): new list of rules with non-intersecting domains.
        """

        new_rules = []
        
        ### CREEPY ###
        if self.rules_name == "CReEPy":
            if not rules:
                return new_rules
            
            new_rules.append(copy.deepcopy(rules[0]))

            for k in range(1, len(rules)):
                last_rule = rules[k - 1]
                rule = rules[k]
                current_bounds = copy.deepcopy(rule["if"]["value"])
                
                for i, var in enumerate(rule["if"]["var"]):
                    # find corresponding variable in the previous rule
                    j = next((y for y, v in enumerate(last_rule["if"]["var"]) if v == var), -1)
                    if j < 0:
                        continue
                    
                    lb, ub = rule["if"]["value"][i]
                    last_lb, last_ub = last_rule["if"]["value"][j]

                    # case 1a: current rule extends below previous lower bound
                    if lb < last_lb:
                        # create new rule
                        # then same as the old
                        values = copy.deepcopy(current_bounds)
                        values[i][1] = last_lb  # shrink upper bound
                        new_rules.append({
                            "if": {"var": rule["if"]["var"], "value": values, "type": rule["if"]["type"]},
                            "then": rule["then"]
                        })

                    # case 1b: current rule extends above previous upper bound
                    if ub > last_ub:
                        # create new rule
                        # then same as the old
                        values = copy.deepcopy(current_bounds)
                        values[i][0] = last_ub  # shrink lower bound
                        new_rules.append({
                            "if": {"var": rule["if"]["var"], "value": values, "type": rule["if"]["type"]},
                            "then": rule["then"]
                        })
                        
                    # adjust the overlapping region in the current rule, with the bound as a small rectangle
                    current_bounds[i][0] = last_lb
                    current_bounds[i][1] = last_ub

        ### CART ###
        elif self.rules_name == "CART":
            if not rules:
                return new_rules
            
            new_rules.append(copy.deepcopy(rules[0]))
            
            for i in range(1, len(rules)):
                rule = rules[i]
                new_rule = copy.deepcopy(rule)
                
                for j in range(i):
                    prev_rule = rules[j]
                    
                    for y in range(len(prev_rule["if"]["var"])):

                        if (
                            y >= len(rule["if"]["var"]) or 
                            rule["if"]["var"][y] != prev_rule["if"]["var"][y] or 
                            rule["if"]["value"][y] != prev_rule["if"]["value"][y]
                        ):
                            
                            # add the opposite constraint to avoid overlap
                            new_rule["if"]["var"].append(prev_rule["if"]["var"][y])
                            new_rule["if"]["value"].append(prev_rule["if"]["value"][y])
                            
                            if prev_rule["if"]["type"][y] in ("<", "<="):
                                new_rule["if"]["type"].append(">=")

                            elif prev_rule["if"]["type"][y] in (">", ">="):
                                new_rule["if"]["type"].append("<=")
                            
                            break
                
                new_rules.append(new_rule)
            
            
            #print(new_rules)
            for rule in new_rules:

                vars_ = rule["if"]["var"]
                values = rule["if"]["value"]
                types = rule["if"]["type"]

                up_bounds, lw_bounds = {}, {}

                for var, val, typ in zip(vars_, values, types):
                    if typ in ("<", "<="):
                        up_bounds[var] = min(up_bounds.get(var, float("inf")), val)
                    elif typ in (">", ">="):
                        lw_bounds[var] = max(lw_bounds.get(var, float("-inf")), val)
                
                new_if = {"var": [], "value": [], "type": []}

                for var, val in lw_bounds.items():
                    new_if["var"].append(var)
                    new_if["value"].append(val)
                    new_if["type"].append(">=")
                    
                for var, val in up_bounds.items():
                    new_if["var"].append(var)
                    new_if["value"].append(val)
                    new_if["type"].append("<=")
                
                rule["if"] = new_if
        
        elif self.rules_name in ("GridREx", "GridEx"):  #no intersections already
            new_rules = rules

        else:
            raise ValueError(f"Unknown rule type: {self.rules_name}")

        return new_rules


    @staticmethod
    def predict(rules: list[dict], data: pd.DataFrame) -> np.ndarray:
        """
        Predict target values using a set of logic rules.

        Args:
            rules (list[dict]): logic rules from get_rules, defining the model.
            data (pd.DataFrame): input data with columns matching input variables and rows as instances.

        Returns:
            np.ndarray: array of predicted target values. If no rule matches an instance, the value is set to np.nan.
        """
        
        results = np.full(data.shape[0], np.nan)
        
        for index, row in data.iterrows():

            for rule in rules:
                rule_conditions = rule["if"]
                all_conditions_met = True

                # check if all "if" conditions of the rule are satisfied
                for var, cond_type, cond_value in zip(rule_conditions["var"], rule_conditions["type"], rule_conditions["value"]):
                    val = row[var]
                    
                    if cond_type == "<" and not val < cond_value:
                        all_conditions_met = False
                        break
                    
                    elif cond_type == "<=" and not val <= cond_value:
                        all_conditions_met = False
                        break
                    
                    elif cond_type == ">" and not val > cond_value:
                        all_conditions_met = False
                        break
                    
                    elif cond_type == ">=" and not val >= cond_value:
                        all_conditions_met = False
                        break
                    
                    elif cond_type == "range" and not (cond_value[0] <= val <= cond_value[1]):
                        all_conditions_met = False
                        break

                if all_conditions_met:
                    # compute the "then" value
                    then_value = rule["then"]["value"][0]
                    var_dict = {}

                    for var in data.columns.values.tolist():
                        var_dict[var] = row[var]
                    
                    if isinstance(then_value, int):
                        results[index] = then_value
                    
                    else:
                        results[index] = eval(then_value, var_dict)

                    break  # stop at first matching rule
        
        return results


def get_linear_expression(expr: str) -> str:
    """
    Converts a linear expression string into a CPLEX-evaluable expression.
    Each variable name in the input string is replaced by a reference to the corresponding CPLEX model variable (via mdl.get_var_by_name("<var>")).

    Args:
        expr (str): linear expression as a string.

    Returns:
        str: expression string where variable names are replaced with mdl.get_var_by_name("<var>").

    Credits: https://github.com/ai-research-disi/Logic_HADA/blob/main/utils/util_functions.py
    """

    l = expr.split()
    
    for i, token in enumerate(l):
        
        try:
            eval(token)
            l[i] = token
        except Exception:
            
            if token in ['+', '-', '*']:
                l[i] = token
            
            else:
                var = f'mdl.get_var_by_name("{token}")'
                l[i] = var
    
    linear_expr = ' '.join(l)

    return linear_expr

