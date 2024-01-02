'''
Class that handles operations that have to be carried out on logic rules.
'''
import ast
import os
import re
import copy

import numpy as np


class LogicModels():
    def __init__(self, db, rules_path, rules_name):
        """Handles all operations on the Logic Model.

        Args:
            db (ConfigDB): ConfigDB instance.
            rules_path (str): local path where the logic_rules are stored.
            name (str): name of the extractor
        """
        if rules_name not in ['GridREx', 'GridEx', 'CReEPy', 'CART']:
            raise AttributeError(f'Wrong rules name {rules_name}. Options: GridREx,  GridEx,  CReEPy,  CART.')
        self.db = db
        self.rules_path = rules_path
        self.rules_name = rules_name


    def __get_rules_path(self, algorithm, hw, target):
        return os.path.join(self.rules_path, f'{self.rules_name}/{algorithm}_{hw}_{target}.txt')




    def get_rules_GridREx(self, algorithm, hw, target):
        """Returns the logic rules for GridREx and CReEPy
           called by get_rules()
        """
        rules_path = self.__get_rules_path(algorithm, hw, target)

        if not os.path.exists(rules_path):
            raise Exception(f'logic_rules for ({algorithm}, {hw}, {target}) not available')
        with open(rules_path, "r") as file:
            lines = file.readlines()
        rules=[]
        for index, line in enumerate(lines):
            if index % 2 == 1:
                interval = {}
                if_constraint = {"var": [], "value": [], "type": []}
                then_constraint = {"var": [], "value": [], "type": ["=="]}
                first, expression = line.split(', '+target+' is ')
                if_parts = first.split('],')
                for i, part in enumerate(if_parts):
                    if i != len(if_parts)-1 :
                        part = part + "]"
                    var, interval_s = part.split(' in ')
                    var = var.strip()
                    if_constraint["var"].append(var)
                    var_interval = ast.literal_eval(interval_s)
                    if_constraint["value"].append(var_interval)
                    if_constraint["type"].append("range")
                then_constraint["var"].append(target)
                then_constraint["value"].append(expression.strip()[0:-1])
                rule = {"if": if_constraint, "then": then_constraint}
                rules.append(rule)
        return rules

    def get_rules_GridEx(self, algorithm, hw, target):
        """Returns the logic rules for GridEx
           called by get_rules()
        """
        rules_path = self.__get_rules_path(algorithm, hw, target)

        if not os.path.exists(rules_path):
            raise Exception(f'logic_rules for ({algorithm}, {hw}, {target}) not available')
        with open(rules_path, "r") as file:
            lines = file.readlines()
        rules=[]
        if algorithm == 'anticipate':
            hyperpar = 'nScenarios'
        else:
            hyperpar = 'nTraces'

        for index, line in enumerate(lines):
            if index % 2 == 1:
                interval = {}
                if_constraint = {"var": [], "value": [], "type": []}
                if_parts = re.split('][.,]', line)
                #print(if_parts)
                for i, part in enumerate(if_parts):
                    if i != len(if_parts)-1 :
                        part = part + "]"
                    if len(part) < 2:
                        continue
                    var, interval_s = part.split(' in ')
                    var = var.strip()
                    if_constraint["var"].append(var)
                    var_interval = ast.literal_eval(interval_s)
                    interval[var] = var_interval
                    if_constraint["value"].append(var_interval)
                    if_constraint["type"].append("range")
                rule = {"if": if_constraint, "then": then_constraint}
                rules.append(rule)
            else:
                then_constraint = {"var": [], "value": [], "type": ["=="]}
                then_constraint["var"].append(target)
                first, expression = line.split(hyperpar+',')
                expression , _ = expression.split(')')
                then_constraint["value"].append(expression.strip())
        return rules

    def get_rules_CART(self, algorithm, hw, target):
        """ Returns the logic rules for CART
           called by get_rules().
        """
        rules_path = self.__get_rules_path(algorithm, hw, target)
        #print(rules_path)
        if not os.path.exists(rules_path):
            raise Exception(f'logic_rules for ({algorithm}, {hw}, {target}) not available')
        with open(rules_path, "r") as file:
            lines = file.readlines()
        rules = []
        if algorithm == 'anticipate':
            hyperpar = 'nScenarios'
        else:
            hyperpar = 'nTraces'

        for index, line in enumerate(lines):
            if index % 2 == 1:
                if_constraint = {"var": [], "value": [], "type": []}
                if_parts = re.split(',', line)
                # print(if_parts)
                for i, part in enumerate(if_parts):
                    if i == len(if_parts) - 1:
                        part = part[0: -2]
                    if len(part) < 2:
                        continue
                    if '=<' in part:
                        con_type = '<='
                    else:
                        if '=>' in part:
                            con_type = '>='
                        else:
                            if '<' in part:
                                con_type = '<'
                            else:
                                if '>' in part:
                                    con_type = '>'

                    var, value_s = re.split('[=]*[<>]', part)
                    var = var.strip()
                    if_constraint["var"].append(var)
                    if_constraint["value"].append(eval(value_s.strip()))
                    if_constraint["type"].append(con_type)
                rule = {"if": if_constraint, "then": then_constraint}
                rules.append(rule)
            else:
                then_constraint = {"var": [], "value": [], "type": ["=="]}
                then_constraint["var"].append(target)
                first, expression = line.split(hyperpar + ',')
                expression, _ = expression.split(')')
                then_constraint["value"].append(expression.strip())
        if index %2 == 0:
            rule = {"if": {"var": [], "value": [], "type": []}, "then": then_constraint}
            rules.append(rule)
        return rules


    def get_rules(self, algorithm, hw, target):
        """Returns the logic rules.

        Args:
            algorithm (str): algorithm id.
            hw (str): hardware platform id
            target (str): target id.

        Raises:
            Exception: if rule is not found

        Returns:
            logic_rules  [{'if': {'var': [...], 'type': ['range'], value:[[lb, up], ...]} ,  'then':{'var': [...], 'type': ['=='], value:[expr, ...]} }, ...]
        """
        return self.get_rules_new(algorithm, hw, target)
        '''
        if self.rules_name == 'GridREx' or self.rules_name == 'CReEPy':
            return self.get_rules_GridREx( algorithm, hw, target)
        if self.rules_name == 'GridEx':
            return self.get_rules_GridEx( algorithm, hw, target)
        if self.rules_name == 'CART':
            return self.get_rules_CART( algorithm, hw, target)'''





    def get_rules_new(self, algorithm, hw, target):
        """Returns the logic rules for GridEx, GridREx CReEPy and CART
           called by get_rules()
        """
        rules_path = self.__get_rules_path(algorithm, hw, target)

        if not os.path.exists(rules_path):
            raise Exception(f'logic_rules for ({algorithm}, {hw}, {target}) not available')
        with open(rules_path, "r") as file:
            lines = file.readlines()
        rules=[]
        if algorithm == 'anticipate':
            hyperpar = 'nScenarios'
        else:
            hyperpar = 'nTraces'
        #identify the rule
        #identify the type
        #parse

        for index, line in enumerate(lines):
            if index % 2 == 0:
                #head
                if bool(re.search(r'\d', line)):
                    then_constraint = {"var": [], "value": [], "type": ["=="]}
                    then_constraint["var"].append(target)
                    first, expression = line.split(hyperpar + ',')
                    expression, _ = expression.split(')')
                    then_constraint["value"].append(expression.strip())
            else:
                #body
                if_constraint = {"var": [], "value": [], "type": []}
                if " is " in line:
                    then_constraint = {"var": [], "value": [], "type": ["=="]}
                    #line, expression = line.split(', ' + target + ' is ')
                    line, expression = line.split( ' '+target + ' is ')
                    line = line.strip()
                    then_constraint["var"].append(target)
                    then_constraint["value"].append(expression.strip()[0:-1])
                if "[" in line:#intervals

                    interval = {}

                    if_parts = re.split('][.,]', line)
                    #print(if_parts)
                    for i, part in enumerate(if_parts):
                        if i != len(if_parts)-1 :
                            part = part + "]"
                        if len(part) < 2:
                            continue
                        var, interval_s = part.split(' in ')
                        var = var.strip()
                        if_constraint["var"].append(var)
                        var_interval = ast.literal_eval(interval_s)
                        interval[var] = var_interval
                        if_constraint["value"].append(var_interval)
                        if_constraint["type"].append("range")
                else:
                    if_parts = re.split(',', line)
                    # print(if_parts)
                    for i, part in enumerate(if_parts):
                        if i == len(if_parts) - 1:
                            part = part[0: -2]
                        if len(part) < 2:
                            continue
                        if '=<' in part:
                            con_type = '<='
                        else:
                            if '=>' in part:
                                con_type = '>='
                            else:
                                if '<' in part:
                                    con_type = '<'
                                else:
                                    if '>' in part:
                                        con_type = '>'

                        var, value_s = re.split('[=]*[<>]', part)
                        var = var.strip()
                        if_constraint["var"].append(var)
                        if_constraint["value"].append(eval(value_s.strip()))
                        if_constraint["type"].append(con_type)


                rule = {"if": if_constraint, "then": then_constraint}
                rules.append(rule)

        if index % 2 == 0:#rule with no body
            rule = {"if": {"var": [], "value": [], "type": []}, "then": then_constraint}
            rules.append(rule)
        return rules

    def reduce_domain(self, rules):
        """
        reduces the domain in which each rule is true, avoiding intersections,
        rules that
        Args:
            rules: logic rules from get_rules

        Returns: new_logic rules with no intersections

        """
        new_rules = []
        if self.rules_name == "CReEPy":
            new_rules.append(copy.deepcopy(rules[0]))
            for k in range(1, len(rules)):
                last_rule = rules[k - 1]
                rule = rules[k]
                current_bounds = copy.deepcopy(rule["if"]["value"])
                for i, var in enumerate(rule["if"]["var"]):
                    j = -1
                    for y, var_1 in enumerate(last_rule["if"]["var"]):
                        if var == var_1:
                            j = y
                            break
                    if j >= 0:
                        lb = rule["if"]["value"][i][0]
                        ub = rule["if"]["value"][i][1]
                        last_lb = last_rule["if"]["value"][j][0]
                        last_ub = last_rule["if"]["value"][j][1]
                        # if last_ub <= lb or ub <= last_lb:
                        #   break;
                        # if lb == last_lb and ub == last_ub:
                        #    continue;
                        if lb < last_lb:
                            # create new rule
                            # then same as the old
                            values = copy.deepcopy(current_bounds)
                            values[i][1] = last_lb  # new ub is lb
                            new_rules.append(
                                {"if": {"var": rule["if"]["var"], "value": values, "type": rule["if"]["type"]},
                                 "then": rule["then"]})

                        if ub > last_ub:
                            # create new rule
                            # then same as the old
                            values = copy.deepcopy(current_bounds)
                            values[i][0] = last_ub  # new lb is ub
                            new_rules.append(
                                {"if": {"var": rule["if"]["var"], "value": values, "type": rule["if"]["type"]},
                                 "then": rule["then"]})
                        # now we have to focus on the other dimensions, with the bound as the small rectangle
                        current_bounds[i][0] = last_lb
                        current_bounds[i][1] = last_ub

        if self.rules_name == "CART":
            new_rules.append(copy.deepcopy(rules[0]))  # the first is not changed
            for i in range(1, len(rules)):
                rule = rules[i]
                new_rule = copy.deepcopy(rule)
                for j in range(i):
                    rule_j = rules[j]
                    for y in range(len(rule_j["if"]["var"])):
                        # if it's not present
                        if y >= len(rule["if"]["var"]) or rule["if"]["var"][y] != rule_j["if"]["var"][y] or rule["if"]["value"][y] != rule_j["if"]["value"][y]:
                            # add the opposite constraint
                            new_rule["if"]["var"].append(rule_j["if"]["var"][y])
                            new_rule["if"]["value"].append(rule_j["if"]["value"][y])
                            if rule_j["if"]["type"][y] == "<=" or rule_j["if"]["type"][y] == "<":
                                new_rule["if"]["type"].append(">=")
                            if rule_j["if"]["type"][y] == ">=" or rule_j["if"]["type"][y] == ">":
                                new_rule["if"]["type"].append("<=")
                            break  # only one
                new_rules.append(new_rule)

            for rule in new_rules:
                vars = rule["if"]["var"]
                values = rule["if"]["value"]
                types = rule["if"]["type"]
                up_bounds = {}
                lw_bounds = {}
                for i in range(len(vars)):
                    var = vars[i]
                    value = values[i]
                    type = types[i]
                    if type == "<=" or type == "<":
                        if var in up_bounds.keys():
                            if value <= up_bounds[var]:
                                up_bounds[var] = value
                        else:
                            up_bounds[var] = value
                    if type == ">=" or type == ">":
                        if var in lw_bounds.keys():
                            if value >= lw_bounds[var]:
                                lw_bounds[var] = value
                        else:
                            lw_bounds[var] = value
                new_if = {}
                new_if["var"] = []
                new_if["type"] = []
                new_if["value"] = []
                for var in lw_bounds.keys():
                    new_if["var"].append(var)
                    new_if["value"].append(lw_bounds[var])
                    new_if["type"].append(">=")
                for var in up_bounds.keys():
                    new_if["var"].append(var)
                    new_if["value"].append(up_bounds[var])
                    new_if["type"].append("<=")
                rule["if"] = new_if
        if self.rules_name == "GridREx" or self.rules_name == "GridEx":  #no intersections already
            new_rules = rules

        return new_rules

    @staticmethod
    def predict(rules, data):
        """
            predicts value of target
            Args:
                rules: logic rules from get_rules, the rules define the model
                data: pandas.DataFrame with the input vars as columns and the instances as rows

            Returns: numpy array containing the results

        """
        results = np.zeros(data.shape[0])
        count = 0
        for index, row in data.iterrows():
            for rule in rules:
                all_conditions = True
                for condition in range(len(rule["if"]["var"])):
                    var = rule["if"]["var"][condition]
                    type = rule["if"]["type"][condition]
                    value = rule["if"]["value"][condition]
                    if type == "<":
                        if row[var] >= value:
                            all_conditions = False
                            break
                    if type == "<=":
                        if row[var] > value:
                            all_conditions = False
                            break
                    if type == ">":
                        if row[var] <= value:
                            all_conditions = False
                            break
                    if type == ">=":
                        if row[var] < value:
                            all_conditions = False
                            break
                    if type == "range":
                        if row[var] < value[0] or row[var] > value[1]:
                            all_conditions = False
                            break
                if all_conditions:
                    # the rule is true and we assign the result
                    var_dict = {}
                    for var in data.columns.values.tolist():
                        var_dict[var] = row[var]
                    value = rule["then"]["value"][0]
                    count += 1
                    if isinstance(value, int):
                        results[index] = value
                    else:
                        res =  eval(value, var_dict)
                        results[index] = res
                    break

            if count != index + 1:
                #if no rule is true
                results[index] = np.nan
                count = index + 1
        return results

def get_linear_expression(s: str):
    """
    Returns the input linear expression with the link to the cplex model variables.
    :param s: string containing the linear expression
    :return:
        A string with where the variables' name in the original linear expression have been replaced by the corresponding
        cplex model variables
    credit https://github.com/ai-research-disi/Logic_HADA/blob/main/utils/util_functions.py
    """
    l = s.split()
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

