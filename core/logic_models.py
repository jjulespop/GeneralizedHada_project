'''
Class that handles operations that have to be carried out on the ML models.
'''
import ast
import os




class LogicModels():
    def __init__(self, db, rules_path):
        """Handles all operations on ML logic_rules.

        Args:
            db (ConfigDB): ConfigDB instance.
            datasets (Datasets): Datasets instance.
            rules_path (str): local path where the logic_rules are stored.
        """
        self.db = db
        self.rules_path = rules_path


    def __get_rules_path(self, algorithm, hw, target):
        return os.path.join(self.rules_path, f'{algorithm}_{hw}_{target}_GridREx.txt')

    def get_rules(self, algorithm, hw, target):
        """Returns the rule (Decision).

        Args:
            algorithm (str): algorithm id.
            hw (str): hardware platform id
            target (str): target id.

        Raises:
            Exception: if rule is not found

        Returns:
            logic_rules  [{'if': {'var': [...], 'type': ['range'], value:[[lb, up], ...]} ,  'then':{'var': [...], 'type': ['=='], value:[expr, ...]} }, ...]
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
                if_constraint = {"var": [], "value": [], "type": ["range"]}
                then_constraint = {"var": [], "value": [], "type": ["=="]}
                first, expression = line.split(', '+target+' is ')
                var, interval_s = first.split(' in ')
                var = var.strip()
                if_constraint["var"].append(var)
                var_interval = ast.literal_eval(interval_s)
                interval[var] = var_interval
                if_constraint["value"].append(var_interval)
                then_constraint["var"].append(target)
                then_constraint["value"].append(expression.strip()[0:-1])
                rule = {"if": if_constraint, "then": then_constraint}
                rules.append(rule)
        return rules


def get_linear_expression(s: str):
    """
    Returns the input linear expression with the link to the cplex model variables.
    :param s: string containing the linear expression
    :return:
        A string with where the variables' name in the original linear expression have been replaced by the corresponding
        cplex model variables
    @author: EleMisi
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

