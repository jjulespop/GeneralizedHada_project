class OptimizationSolution():
    """
    Represents a solution produced by the HADA algorithm.
    """
    
    def __init__(self, chosen_hw = None, hyperparams_values = None, targets_values = None, num_variables = None, num_constraints = None):
        self.chosen_hw = chosen_hw
        self.hyperparams_values = hyperparams_values
        self.targets_values = targets_values
        self.num_variables = num_variables
        self.num_constraints = num_constraints


    def __str__(self):
        return f'chosen hw: {self.chosen_hw}; hyperparams values: {self.hyperparams_values}; targets values: {self.targets_values}; num_variables: {self.num_variables}; num_constraints: {self.num_constraints}'