'''
Class that handles operations that have to be carried out on logic rules.
'''
import ast
import os
import re




class LogicModels():
    def __init__(self, db, rules_path, rules_name):
        """Handles all operations on the Logic Model.

        Args:
            db (ConfigDB): ConfigDB instance.
            rules_path (str): local path where the logic_rules are stored.
            name (str): name of the extractor
        """
        if rules_name not in ['GridREx', 'GridEx', 'CReEPY', 'CART']:
            raise AttributeError(f'Wrong rules name {rules_name}. Options: GridREx,  GridEx,  CReEPY,  CART.')
        self.db = db
        self.rules_path = rules_path
        self.rules_name = rules_name


    def __get_rules_path(self, algorithm, hw, target):
        return os.path.join(self.rules_path, f'{self.rules_name}/{algorithm}_{hw}_{target}.txt')




    def get_rules_GridREx(self, algorithm, hw, target):
        """Returns the logic rules for CART
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
        """Returns the logic rules for GridEx and CReEPY
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
        print(rules_path)
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
                    if '<=' in part:
                        con_type = '<='
                    else:
                        if '>=' in part:
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
        if self.rules_name == 'GridREx' or self.rules_name == 'CReEPY':
            return self.get_rules_GridREx( algorithm, hw, target)
        if self.rules_name == 'GridEx':
            return self.get_rules_GridEx( algorithm, hw, target)
        if self.rules_name == 'CART':
            return self.get_rules_CART( algorithm, hw, target)





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

