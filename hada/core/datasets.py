import os
import requests
import numpy as np
from abc import ABC,abstractmethod
from collections import defaultdict
from io import StringIO
from urllib.parse import urljoin
import pandas as pd
from hada.core.optimization_request import OptimizationRequest
from hada.core.logic_models import LogicModels
from hada.core.configdb import ConfigDB

class Datasets(ABC):
    """Class that handles all the operations on the datasets."""


    @abstractmethod
    def __init__(self, db: ConfigDB):
        """
        Args:
            db (ConfigDB): instance of the configuration database.
        """
        self.db = db


    @classmethod
    def from_local(cls, db: ConfigDB, data_path: str):
        """
        Create a Datasets instance using local datasets.

        Args:
            db (ConfigDB): instance of ConfigDB.
            data_path (str): local path containing the datasets.

        Returns:
            Datasets: instance of Datasets.
        """
        return DatasetsLocal(db, data_path)


    @classmethod
    def from_remote(cls, db, base_url: str):
        """
        Create a Datasets instance using remote datasets (VM storage ervice).

        Args:
            db (ConfigDB): instance of ConfigDB.
            base_url (str): complete URL relative to the service that handles the datasets.

        Returns:
            Datasets: instance of Datasets.
        """
        return DatasetsRemote(db, base_url)


    @abstractmethod
    def get_dataset(self, algorithm: str, hw) -> pd.DataFrame:
        """Returns the dataset (Pandas DataFrame) relative to the (algorithm, hw), if present."""
        pass


    def _check_dataset_consistency(self, df: pd.DataFrame, algorithm: str, hw: str) -> None:
        """
        Validate that the dataset matches the configuration for a given (algorithm, hardware) pair.

        Checks that:
        1. All expected columns (hyperparameters, input vars, targets) are present and no extras exist.
        2. All columns contain numeric data.
        3. Data types are consistent with configuration specifications ('int', 'float', 'bin').

        Args:
            df (pd.DataFrame): the dataset to validate.
            algorithm (str): algorithm identifier.
            hw (str): hardware identifier.

        Raises:
            AttributeError: if expected columns are missing or contain non-numeric data.
            ValueError: if a column violates declared type constraints.
        """


        hyperparams = self.db.get_hyperparams(algorithm)
        input_vars = self.db.get_input_vars(algorithm)
        targets = self.db.get_targets(algorithm)

        if 'price' in targets:
            targets.remove('price')

        expected_columns = set(hyperparams + input_vars + targets)
        actual_columns = set(df.columns)

        # check for missing or extra columns
        if expected_columns != actual_columns:

            missing = expected_columns - actual_columns
            extra = actual_columns - expected_columns

            raise AttributeError(
                f"Dataset for algorithm '{algorithm}' on hardware '{hw}' "
                f"has inconsistent columns.\n"
                f"Missing: {sorted(missing) if missing else 'None'}\n"
                f"Unexpected: {sorted(extra) if extra else 'None'}"
        )
         
        #from pandas.api.types import is_numeric_dtype
        type_per_var = self.db.get_type_per_var(algorithm)

        for column in df.columns:

            series = df[column]
            expected_dtype = type_per_var[column]

            if not pd.api.types.is_numeric_dtype(series):
                raise AttributeError(f"Column '{column}' in dataset ({algorithm}, {hw}) must be numeric, found {series.dtype}.")

            # checking consistency with vartype declared in configs: int, float or bin
            # float already checked: if it's numerical it can be interpreted as float

            if expected_dtype == 'int' and not pd.api.types.is_integer_dtype(series):
                raise ValueError(f"Column '{column}' in dataset ({algorithm}, {hw}) is expected to be integer but contains non-integer values.")
            
            elif expected_dtype == 'bin' and set(df[column].unique()) != {0, 1}:
                unique_values = set(series.dropna().unique())
                raise ValueError(f"Column '{column}' in dataset ({algorithm}, {hw}) is expected to be binary, but found values: {sorted(unique_values)}")


    def extract_var_bounds(self, algorithm: str) -> tuple[dict, dict]:
        """
        Compute lower and upper bounds for each variable (hyperparameters, inputs, and targets).

        The method uses bounds specified in the configuration when available.
        If a bound (LB/UB) is missing in the config, it is inferred from the datasets across all hardware platforms.

        Args:
            algorithm (str): algorithm for which to compute variable bounds.

        Returns:
            tuple[dict, dict]:
                - lb_per_var: lower bounds for each variable.
                - ub_per_var: upper bounds for each variable.

        Raises:
            ValueError: if inferred bounds are incompatible with declared variable types.
        """

        # retrieving LBs/UBs from configs
        lb_per_var = self.db.get_lb_per_var(algorithm)
        ub_per_var = self.db.get_ub_per_var(algorithm)

        # identify variables missing lower or upper bounds
        lb_missing_vars = [var for var,lb in lb_per_var.items() if lb is None]
        ub_missing_vars = [var for var,ub in ub_per_var.items() if ub is None]
        missing_vars = set(lb_missing_vars + ub_missing_vars)

        # at least one bound to be extracted
        if missing_vars:

            # prepare containers for collected min/max values across hardware datasets
            all_mins_per_var = defaultdict(list)
            all_maxes_per_var = defaultdict(list)

            # aggregate observed minima/maxima across all hardware platforms
            for hw in self.db.get_hws(algorithm):
                dataset = self.get_dataset(algorithm, hw)

                for var in lb_missing_vars:
                    if var in dataset:
                        all_mins_per_var[var].append(dataset[var].min())

                for var in ub_missing_vars:
                    if var in dataset:
                        all_maxes_per_var[var].append(dataset[var].max())

            # compute overall min/max for missing bounds
            for var in lb_missing_vars:
                lb_per_var[var] = min(all_mins_per_var[var])

                if type(lb_per_var[var]) is np.int64:
                    lb_per_var[var] = int(lb_per_var[var])
            
            for var in ub_missing_vars:
                ub_per_var[var] = max(all_maxes_per_var[var])
                
                if type(ub_per_var[var]) is np.int64:
                    ub_per_var[var] = int(ub_per_var[var])

            # check that computed bounds match expected variable types
            type_per_var = self.db.get_type_per_var(algorithm)

            for var, dtype in type_per_var.items():
                var_lb = lb_per_var[var]
                var_ub = ub_per_var[var]

                if dtype == 'int':
                    if type(var_lb) is not int or type(var_ub) is not int:
                        raise ValueError(f"Variable '{var}' expects integer bounds, but found types ({type(var_lb).__name__}, {type(var_ub).__name__}).")
                
                elif dtype == 'bin':
                    if (var_lb not in [0,1]) or (var_ub not in [0,1]):
                        raise ValueError(f"Variable '{var}' is binary but has invalid bounds: LB={var_lb}, UB={var_ub}. Expected 0 or 1.")

        return lb_per_var, ub_per_var


    def get_var_bounds_all(self, request: OptimizationRequest) -> dict:
        """
        Compute upper and lower bounds of each variable, including price.
        If UB/LB specified in configs, use that instead of extracting from data.

        Args:
            request (OptimizationRequest): instance of OptimizationRequest.

        Returns:
            var_bounds (dict): lower bound and upper bound for each variable, including price.
        """

        lb_per_var, ub_per_var = self.extract_var_bounds(request.algorithm)

        if request.target == 'price' or 'price' in request.user_constraints.get_constraints():
            lb_per_var['price'] = min(request.hws_prices.get_prices_per_hw().values())
            ub_per_var['price'] = max(request.hws_prices.get_prices_per_hw().values())

        var_bounds = {var: {'lb':lb_per_var[var], 'ub':ub_per_var[var]} for var in lb_per_var}
        
        return var_bounds
        

    def get_robust_coeff(self, logic_models: LogicModels, request: OptimizationRequest) -> dict:
        """
        Compute robustness coefficients for each predictive model, according to the specified robustness factor.

        Args:
            logic_models (LogicModels): object handling logic-based models (rule-based predictions).
            request (OptimizationRequest): user request.

        Returns:
            robust_coeff (dict): dictionary {(hardware, target): robustness coefficient}; None if no robustness factor is set.
        """

        # checking if robustness factor is defined
        if request.robustness_fact is None:
            return None

        algorithm = request.algorithm
        robustness_fact = request.robustness_fact

        hyperparams = self.db.get_hyperparams(algorithm)
        input_vars = self.db.get_input_vars(algorithm)
        targets = self.db.get_targets(algorithm)
        hardwares = self.db.get_hws(algorithm)

        robust_coeff = {}

        for hw in hardwares:
            dataset = self.get_dataset(algorithm, hw)

            for target in targets:
                if target == "price":
                    robust_coeff[(hw, target)] = 0
                    continue

                rules = logic_models.get_rules(algorithm, hw, target)

                try:
                    predictions = logic_models.predict(rules, dataset[hyperparams + input_vars])
                    errors = (dataset[target] - predictions).abs()
                except Exception as e:
                    raise RuntimeError(
                        f"Error computing predictions for target '{target}' on hardware '{hw}': {e}"
                    )

                # computing robustness coefficient: std(error) * quantile(error)
                error_std = errors.std()
                error_quantile = errors.quantile(robustness_fact)
                robust_coeff[(hw, target)] = error_std * error_quantile

        return robust_coeff


class DatasetsLocal(Datasets):
    """Handles datasets stored in the local filesystem."""


    def __init__(self, db: ConfigDB, data_path: str):
        super().__init__(db)
        self.data_path = data_path


    def get_dataset(self, algorithm: str, hw: str) -> pd.DataFrame:
        """
        Load a dataset from the local filesystem.

        Args:
            algorithm (str): algorithm name.
            hw (str): hardware used.

        Returns:
            pd.DataFrame: dataset.
        """

        dataset_path = os.path.join(self.data_path, f'{algorithm}_{hw}.csv')

        if not os.path.exists(dataset_path):
            raise FileNotFoundError(f'Dataset for ({algorithm}, {hw}) not found at {dataset_path}.')

        try:
            dataset = pd.read_csv(dataset_path)
        except Exception as e:
            raise ValueError(f"Failed to read dataset CSV ({dataset_path}): {e}")

        # checking if data complies to configs
        self._check_dataset_consistency(dataset, algorithm, hw)

        return dataset


class DatasetsRemote(Datasets):
    """Handles retrieval of datasets from a remote storage service."""


    def __init__(self, db: ConfigDB, base_url: str):
        super().__init__(db)
        self.base_url = base_url


    def get_dataset(self, algorithm: str, hw: str) -> pd.DataFrame:
        """
        Retrieve a dataset from the remote service.

        Args:
            algorithm (str): algorithm name.
            hw (str): hardware identifier.

        Returns:
            pd.DataFrame: dataset.
        """

        dataset_url = urljoin(self.base_url, f'/datasets/{algorithm}/{hw}')

        try:
            response = requests.get(dataset_url)
            response.raise_for_status()
        except requests.RequestException as e:
            raise ConnectionError(f"Failed to fetch dataset ({algorithm}, {hw}) from {dataset_url}: {e}")
        
        try:
            dataset = pd.read_csv(StringIO(response.text))
        except Exception as e:
            raise ValueError(f"Failed to parse CSV for ({algorithm}, {hw}): {e}")

        # checking if data complies to configs
        self._check_dataset_consistency(dataset, algorithm, hw)

        return dataset
