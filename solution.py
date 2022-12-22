class OptimizationSolution():
    '''Class containing a solution produced by HADA.'''
    def __init__(self, chosen_hw, hyperparams_values, targets_values):
        self.chosen_hw = chosen_hw
        self.hyperaparams_values = hyperparams_values
        self.targets_values = targets_values

    def __str__(self):
        return f'chosen hw: {self.chosen_hw}; hyperparams values: {self.hyperaparams_values}; targets values: {self.targets_values}'
