from hada.core.configdb import ConfigDB


class Inputs():
    """
    Represents user-defined inputs to be included in an optimization request.
    """
    
    def __init__(self, configdb: ConfigDB, algorithm: str) -> None:
        """
        Initialize an Inputs instance.

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
        self.inputs = {}


    def add_input(self, input_var: str, value: float | int) -> None:
        """
        Add an input to the request.

        Args:
            input_var (str): input variable name.
            value (float | int): constraint value.

        Raises:
            AttributeError: if input variable is invalid, or value is not numeric.
        """

        if input_var not in self.db.get_input_vars(self.algorithm):
            raise AttributeError(f'Input variable {input_var} not available for algorithm {self.algorithm}.')
        
        if not isinstance(value, (int, float)):
            raise AttributeError("Constraint value must be numerical (int or float).")

        self.inputs[input_var] = value


    def get_inputs(self) -> dict[str, float | int]:
        return self.inputs
