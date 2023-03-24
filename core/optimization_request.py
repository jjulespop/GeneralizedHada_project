class OptimizationRequest():
    """Class that represents and handles an optimization request for HADA. Arguments are checked."""
    def __init__(self,
                 db,
                 algorithm,
                 target,
                 inputs,
                 opt_type,
                 robustness_fact,
                 user_constraints,
                 hws_prices):

        if algorithm not in db.get_algorithms():
            raise AttributeError(f'Algorithm {algorithm} not available.')
        self.algorithm = algorithm

        if target not in db.get_targets(algorithm):
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

        if not isinstance(inputs, Inputs):
            raise AttributeError("Input must be specified via Inputs class.")
        if set(inputs.get_inputs().keys()) != set(db.get_input_vars(algorithm)):
            raise AttributeError("Must set a value for each input variable.")
        self.inputs = inputs

        # no user input version; just read from config
        # otherwise we expect prices from user and what's in the configs is only for guidance.
        #self.prices = self.db.get_hw_prices(algorithm)

        if not isinstance(hws_prices, HardwarePrices):
            raise AttributeError("Hardware prices must be specified via HardwarePrices class.")
        self.hws_prices = hws_prices


class UserConstraints():
    """Class that represents an user's constraints to be included in a Request. Arguments are checked."""
    def __init__(self, configdb, algorithm) -> None:

        self.db = configdb

        if algorithm not in self.db.get_algorithms():
            raise AttributeError(f'Algorithm {algorithm} not available.')
        self.algorithm = algorithm

        # target : (type, value)
        self.constraints =  {}

    def add_constraint(self, target, constr_type, value):
        if target not in self.db.get_targets(self.algorithm):
            raise AttributeError(f'Target {target} not available for algorithm {self.algorithm}.')

        if constr_type not in ['eq', 'leq', 'geq']:
            raise AttributeError("Constraint type can only be one of 'eq', 'leq', 'geq'.")

        if type(value) not in [float, int]:
            raise AttributeError("Constraint value must be numerical.")

        self.constraints[target] = (constr_type, value)

    def get_constraints(self):
        return self.constraints

class Inputs():
    """Class that represents an user's input to be included in a Request. Arguments are checked."""
    def __init__(self, configdb, algorithm) -> None:

        self.db = configdb

        if algorithm not in self.db.get_algorithms():
            raise AttributeError(f'Algorithm {algorithm} not available.')
        self.algorithm = algorithm

        # target : (type, value)
        self.inputs = {}

    def add_input(self, input_var, value):
        if input_var not in self.db.get_input_vars(self.algorithm):
            raise AttributeError(f'Input variable {input_var} not available for algorithm {self.algorithm}.')
        if type(value) not in [float, int]:
            raise AttributeError("Input value must be numerical.")

        self.inputs[input_var] = value

    def get_inputs(self):
        return self.inputs


class HardwarePrices():
    """Class that represents the chosen price for each hw platform (algorithm-specific). Arguments are checked."""
    def __init__(self, configdb, algorithm) -> None:

        self.db = configdb

        if algorithm not in self.db.get_algorithms():
            raise AttributeError(f'Algorithm {algorithm} not available.')
        self.algorithm = algorithm

        # hw : price
        # loading default values when specified
        self.__price_per_hw =  {hw: price 
                                for hw, price in self.db.get_prices_per_hw(self.algorithm).items()
                                if price}

    def add_hw_price(self, hw, price):
        if hw not in self.db.get_hws(self.algorithm):
            raise AttributeError(f'Hardware platform {hw} not available for algorithm {self.algorithm}.')

        # ignore if price is None
        if price is None:
            return

        if type(price) not in [float, int]:
            raise AttributeError("Price must be numerical.")

        self.__price_per_hw[hw] = price

    def get_prices_per_hw(self):
        # checking that all prices for the algorithms are specified
        hws = self.db.get_hws(self.algorithm)

        if not set(hws) == set(self.__price_per_hw.keys()):
            raise AttributeError("Prices for all hardware platforms related to the algorithm must be specified when the target is 'price' or 'price' is constrainted.")
        return self.__price_per_hw


class OptimizationSolution():
    '''Class containing a solution produced by HADA.'''
    def __init__(self, chosen_hw, hyperparams_values, targets_values, num_variables=None, num_constraints=None):
        self.chosen_hw = chosen_hw
        self.hyperparams_values = hyperparams_values
        self.targets_values = targets_values
        self.num_variables = num_variables
        self.num_constraints = num_constraints

    def __str__(self):
        return f'chosen hw: {self.chosen_hw}; hyperparams values: {self.hyperparams_values}; targets values: {self.targets_values}; num_variables: {self.num_variables}; num_constraints: {self.num_constraints}'
