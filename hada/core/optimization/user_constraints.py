from hada.core.configdb import ConfigDB


class UserConstraints():
    """
    Represents user-defined constraints to be included in an optimization request.
    """
    
    def __init__(self, configdb: ConfigDB, algorithm: str) -> None:
        """
        Initialize a UserConstraints instance.

        Args:
            configdb (ConfigDB): configuration database containing algorithm info.
            algorithm (str): algorithm to which the constraints refer.

        Raises:
            AttributeError: if the algorithm is not available in the database.
        """

        self.db = configdb

        if algorithm not in self.db.get_algorithms():
            raise AttributeError(f'Algorithm {algorithm} not available.')
        
        self.algorithm = algorithm
        self.constraints =  {}


    def add_constraint(self, target: str, constr_type: str, value: float | int) -> None:
        """
        Add a constraint to the request.

        Args:
            target (str): target variable ('time', 'memory').
            constr_type (str): constraint type.
            value (float | int): constraint value.

        Raises:
            AttributeError: if target or constraint type is invalid, or value is not numeric.
        """

        valid_types = {"eq", "leq", "geq"}

        if target not in self.db.get_targets(self.algorithm):
            raise AttributeError(f'Target {target} not available for algorithm {self.algorithm}.')

        if constr_type not in valid_types:
            raise AttributeError(f"Invalid constraint type '{constr_type}'. Must be one of {valid_types}.")

        if not isinstance(value, (int, float)):
            raise AttributeError("Constraint value must be numerical (int or float).")

        self.constraints[target] = (constr_type, value)


    def get_constraints(self) -> dict[str, tuple[str, float | int]]:
        return self.constraints
