from hada.core.config.configdb import ConfigDB
from hada.core.optimization.user_constraints import UserConstraints
from hada.core.optimization.hardware_prices import HardwarePrices
from hada.core.optimization.inputs import Inputs



class OptimizationRequest():
    """
    Represents and validates an optimization request for the HADA algorithm.
    
    Each request defines the optimization problem context, including the target variable,
    optimization objective, robustness factor, user constraints, and hardware prices.
    """
    
    def __init__(self,
                 db: ConfigDB,
                 algorithm: str,
                 target: str,
                 objective: str,
                 robustness_factor: float | int | None,
                 user_constraints: UserConstraints,
                 hws_prices: HardwarePrices):
        """
        Initialize an OptimizationRequest instance.

        Args:
            db (ConfigDB): configuration database instance.
            algorithm (str): algorithm identifier.
            target (str): optimization target variable.
            objective (str): optimization direction ('min' or 'max').
            robustness_factor (float | int | None): robustness coefficient.
            user_constraints (UserConstraints): user-defined constraints.
            hws_prices (HardwarePrices): hardware pricing information.

        Raises:
            AttributeError: If any argument fails validation.
        """

        if algorithm not in db.get_algorithms():
            raise AttributeError(f'Algorithm {algorithm} not available.')
        self.algorithm = algorithm

        if target not in db.get_targets(algorithm):
            raise AttributeError(f'Target {target} not available for algorithm {algorithm}.')
        self.target = target

        if objective not in ['min', 'max']:
            raise AttributeError("Optimization type must be either 'min' or 'max'.")
        self.objective = objective

        if not isinstance(robustness_factor, (int, float)) and robustness_factor is not None:
            raise AttributeError('Robustness factor must be numeric or None.')
        self.robustness_fact = robustness_factor

        if not isinstance(user_constraints, UserConstraints):
            raise AttributeError("User constraints must be an instance of UserConstraints class.")
        self.user_constraints = user_constraints

        if not isinstance(hws_prices, HardwarePrices):
            raise AttributeError("Hardware prices must be an instance of HardwarePrices class.")
        self.hws_prices = hws_prices


class OptimizationRequestTest():
    """
    Represents and validates an optimization request for the HADA algorithm. Same as above + inputs.
    """    
    
    def __init__(self,
                 db: ConfigDB,
                 algorithm: str,
                 target: str,
                 inputs: Inputs,
                 objective: str,
                 robustness_factor: float | int | None,
                 user_constraints: UserConstraints,
                 hws_prices: HardwarePrices):
        """
        Initialize an OptimizationRequest instance.

        Args:
            db (ConfigDB): configuration database instance.
            algorithm (str): algorithm identifier.
            target (str): optimization target variable.
            inputs (Inputs): used-defined inputs.
            objective (str): optimization direction ('min' or 'max').
            robustness_factor (float | int | None): robustness coefficient.
            user_constraints (UserConstraints): user-defined constraints.
            hws_prices (HardwarePrices): hardware pricing information.

        Raises:
            AttributeError: If any argument fails validation.
        """

        if algorithm not in db.get_algorithms():
            raise AttributeError(f'Algorithm {algorithm} not available.')
        self.algorithm = algorithm

        if target not in db.get_targets(algorithm):
            raise AttributeError(f'Target {target} not available for algorithm {algorithm}.')
        self.target = target

        if objective not in ['min', 'max']:
            raise AttributeError("Optimization type must be either 'min' or 'max'.")
        self.objective = objective

        if not isinstance(robustness_factor, (int, float)) and robustness_factor is not None:
            raise AttributeError('Robustness factor must be numeric or None.')
        self.robustness_fact = robustness_factor

        if not isinstance(user_constraints, UserConstraints):
            raise AttributeError("User constraints must be an instance of UserConstraints class.")
        self.user_constraints = user_constraints

        if not isinstance(inputs, Inputs):
            raise AttributeError("Input must be an instance of Inputs class.")
        if set(inputs.get_inputs().keys()) != set(db.get_input_vars(algorithm)):
            raise AttributeError("Must provide a value for each input variable.")
        self.inputs = inputs

        if not isinstance(hws_prices, HardwarePrices):
            raise AttributeError("Hardware prices must be an instance of HardwarePrices class.")
        self.hws_prices = hws_prices
