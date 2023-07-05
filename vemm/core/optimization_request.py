class OptimizationRequest():
    """Class that represents and handles an optimization request for HADA. Arguments are checked."""
    def __init__(self,
                 db,
                 algorithm,
                 target,
                 opt_type,
                 robustness_fact,
                 user_constraints,
                 hws_prices,
                 inputs=None):

        self.input_dependent=False
        if inputs:
            self.input_dependent=True
            if not isinstance(inputs, Inputs):
                raise AttributeError("Inputs must be specified via Inputs class.")
            self.inputs = inputs

        if algorithm not in db.get_algorithms(self.input_dependent):
            raise AttributeError(f'Algorithm {algorithm} not available.')
        self.algorithm = algorithm

        if target not in db.get_targets(algorithm, self.input_dependent):
            raise AttributeError(f'Target {target} not available for algorithm {algorithm}.')
        self.target = target

        if opt_type not in ['min', 'max']:
            raise AttributeError("Optimization type can only be one of 'min', 'max'.")
        self.opt_type = opt_type

        if not (type(robustness_fact) in [int, float] or robustness_fact is None):
            raise AttributeError('Robustness factor must be numerical or None.')
        self.robustness_fact = robustness_fact

        if not isinstance(user_constraints, UserConstraints):
            raise AttributeError("User constraints must be specified via UserConstraints class.")
        self.user_constraints = user_constraints

        # no user input version; just read from config
        # otherwise we expect prices from user and what's in the configs is only for guidance.
        #self.prices = self.db.get_hw_prices(algorithm)

        if not isinstance(hws_prices, HardwarePrices):
            raise AttributeError("Hardware prices must be specified via HardwarePrices class.")
        self.hws_prices = hws_prices

        self.is_case_dependent = False
        if inputs:
            self.is_case_dependent = True
            if not isinstance(inputs, Inputs):
                raise AttributeError("Hardware prices must be specified via HardwarePrices class.")
            self.inputs = inputs

    def is_input_dependent(self):
        return self.input_dependent

class Inputs():
    """Class that represents an user's input to be included in a Request. Arguments are checked."""
    def __init__(self, configdb, algorithm) -> None:

        self.db = configdb

        if algorithm not in self.db.get_algorithms(input_dependent=True):
            raise AttributeError(f'Algorithm {algorithm} not available.')
        self.algorithm = algorithm

        self.type_per_input = self.db.get_type_per_input(algorithm)

        # target : (type, value)
        self.inputs = {}

    def add_input(self, input_var, value):
        if input_var not in self.db.get_inputs(self.algorithm):
            raise AttributeError(f'Input variable {input_var} not available for algorithm {self.algorithm}.')
        
        # check type for input value
        input_type = self.type_per_input[input_var]
        if input_type == 'str' and type(value) is not str:
                raise ValueError(f"Input {input_var} must be a string.")
        if input_type == 'bin' and (type(value) is not int or value not in [0,1]):
                raise ValueError(f"Input {input_var} must be a 0 or 1 (bin).")
        if input_type == 'float' and (type(value) not in [float, int]):
                raise ValueError(f"Input {input_var} must be numerical.")
        if input_type == 'int' and type(value) is not int:
                raise ValueError(f"Input {input_var} must be an integer.")

        self.inputs[input_var] = value

    def get_inputs(self):
        return self.inputs


class UserConstraints():
    """Class that represents an user's constraints to be included in a Request. Arguments are checked."""
    def __init__(self, configdb, algorithm, input_dependent=False) -> None:

        self.db = configdb
        self.input_dependent = input_dependent

        if algorithm not in self.db.get_algorithms(self.input_dependent):
            raise AttributeError(f'Algorithm {algorithm} not available.')
        self.algorithm = algorithm

        # target : (type, value)
        self.constraints =  {}

    def add_constraint(self, target, constr_type, value):
        if target not in self.db.get_targets(self.algorithm, self.input_dependent):
            raise AttributeError(f'Target {target} not available for algorithm {self.algorithm}.')

        if constr_type not in ['eq', 'leq', 'geq']:
            raise AttributeError("Constraint type can only be one of 'eq', 'leq', 'geq'.")

        # constraints are on targets, and targets can only be numerical
        if type(value) not in [float, int]:
            raise AttributeError("Constraint value must be numerical.")

        self.constraints[target] = (constr_type, value)

    def get_constraints(self):
        return self.constraints


class HardwarePrices():
    """Class that represents the chosen price for each hw platform (algorithm-specific). Arguments are checked."""
    def __init__(self, configdb, algorithm, input_dependent=False) -> None:

        self.db = configdb
        self.input_dependent = input_dependent

        if algorithm not in self.db.get_algorithms(self.input_dependent):
            raise AttributeError(f'Algorithm {algorithm} not available.')
        self.algorithm = algorithm

        # hw : price
        # loading default values when specified
        self.__price_per_hw =  {hw: price 
                                for hw, price in self.db.get_prices_per_hw(self.algorithm, self.input_dependent).items()
                                if price}

    def add_hw_price(self, hw, price):
        if hw not in self.db.get_hws(self.algorithm, self.input_dependent):
            raise AttributeError(f'Hardware platform {hw} not available for algorithm {self.algorithm}.')

        # ignore if price is None
        if price is None:
            return

        if type(price) not in [float, int]:
            raise AttributeError("Price must be numerical.")

        self.__price_per_hw[hw] = price

    def get_prices_per_hw(self):
        # checking that all prices for the algorithms are specified
        hws = self.db.get_hws(self.algorithm, self.input_dependent)

        if not set(hws) == set(self.__price_per_hw.keys()):
            raise AttributeError("Prices for all hardware platforms related to the algorithm must be specified when the target is 'price' or 'price' is constrainted.")
        return self.__price_per_hw


class OptimizationSolution():
    '''Class containing a solution produced by HADA.'''
    def __init__(self, chosen_hw, hyperparams_values, targets_values):
        self.chosen_hw = chosen_hw
        self.hyperparams_values = hyperparams_values
        self.targets_values = targets_values

    def __str__(self):
        return f'chosen hw: {self.chosen_hw}; hyperparams values: {self.hyperparams_values}; targets values: {self.targets_values}'
