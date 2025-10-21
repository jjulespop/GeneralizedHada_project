import os
import requests
import pickle
import numpy as np
import pandas as pd
from abc import ABC, abstractmethod
from collections import defaultdict
from io import StringIO
from urllib.parse import urljoin
from hada.core.config.configdb import ConfigDB
from hada.core.models.ml_models import MLModels
from hada.core.optimization.optimization_request import OptimizationRequest


class Datasets(ABC):
    """Class that handles all the operations on the datasets.
        Version with Expander for MLModels class.
    """

    @abstractmethod
    def __init__(self, db: ConfigDB, categories_path: str):
        self.db = db 
        # handles expansion of str hyperparameters (one-hot encoding)
        self.expander = StrExpander(self, categories_path)


    @classmethod
    def from_local(cls, db, data_path, categories_path):
        """Initialize Datasets using local datasets.

        Args:
            db (ConfigDB): instance of ConfigDB.
            data_path_no_inp (str): local path containing the datasets (non input-dependent case).
            data_path_inp (str): local path containing the datasets (input-dependent case).

        Returns:
            Datasets: instance of Datasets.
        """
        return DatasetsLocal(db, data_path, categories_path)


    @classmethod
    def from_remote(cls, db, address, categories_path):
        """Initialize Datasets using remote datasets (VM storage ervice).

        Args:
            db (ConfigDB): instance of ConfigDB.
            address (str): complete URL relative to the service that handles the datasets.

        Returns:
            Datasets: instance of Datasets.
        """
        return DatasetsRemote(db, address, categories_path)


    @abstractmethod
    def get_raw_dataset(self, algorithm: str, hw) -> pd.DataFrame:
        """Returns the dataset (Pandas DataFrame) relative to the (algorithm, hw), if present. No categorical expansion."""
        pass


    @abstractmethod
    def get_dataset(self, algorithm: str, hw) -> pd.DataFrame:
        """Returns the dataset (Pandas DataFrame) relative to the (algorithm, hw), if present. Includes categorical expansion."""
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
        targets = self.db.get_targets(algorithm)
        inputs = self.db.get_inputs(algorithm)

        if 'price' in targets:
            targets.remove('price')

        expected_columns = set(hyperparams + inputs + targets)
        actual_columns = set(df.columns)

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
        numerical_vars = [var for var in type_per_var if var not in self.db.get_str_vars(algorithm)]
        
        for column in df.columns:
            series = df[column]
            expected_dtype = type_per_var[column]

            if column in numerical_vars and not pd.api.types.is_numeric_dtype(series):
                raise AttributeError(f"Column '{column}' in dataset ({algorithm}, {hw}) must be numeric, found {series.dtype}.")

            # checking consistency with vartype declared in configs: int, float or bin
            # float already checked: if it's numerical it can be interpreted as float
            if expected_dtype == 'int' and not pd.api.types.is_integer_dtype(series):
                raise ValueError(f"Column '{column}' in dataset ({algorithm}, {hw}) is expected to be integer but contains non-integer values.")
            
            elif expected_dtype == 'bin' and set(df[column].unique()) != {0, 1}:
                unique_values = set(series.dropna().unique())
                raise ValueError(f"Column '{column}' in dataset ({algorithm}, {hw}) is expected to be binary, but found values: {sorted(unique_values)}")


    def extract_var_bounds(self, algorithm):
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
        # check if both UB and LB are specified in the configs
        # otherwise add to "missing_bounds"; if any extract from data and calculate those

        # retrieving LBs/UBs from configs
        lb_per_var = self.db.get_lb_per_var(algorithm)
        ub_per_var = self.db.get_ub_per_var(algorithm)

        str_vars = self.db.get_str_vars(algorithm)
        # # identify variables missing lower or upper bounds; skipping str variables
        lb_missing_vars = [var for var,lb in lb_per_var.items() if lb is None and var not in str_vars]
        ub_missing_vars = [var for var,ub in ub_per_var.items() if ub is None and var not in str_vars]
        missing_vars = set(lb_missing_vars + ub_missing_vars)

        # at least one bound to be extracted
        if missing_vars:
            # read one HW config at a time
            # extract needed mins and max
            # take overall min of minima and max of maxima
            all_mins_per_var = defaultdict(list)
            all_maxes_per_var = defaultdict(list)

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

            # checking that dtypes of variables are compatible with the bounds
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


    def get_var_bounds_all(self, request: OptimizationRequest):
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

        var_bounds = {var: {'lb':lb_per_var[var], 'ub':ub_per_var[var]}
                        for var in lb_per_var}
        return var_bounds


    def get_robust_coeff(self, models: MLModels, request: OptimizationRequest) -> dict:
        """
        Compute robustness coefficients for each predictive model, according to the specified robustness factor.

        Args:
            logic_models (LogicModels): object handling logic-based models (rule-based predictions).
            request (OptimizationRequest): user request.

        Returns:
            robust_coeff (dict): dictionary {(hardware, target): robustness coefficient}; None if no robustness factor is set.
        """
        if request.robustness_fact or request.robustness_fact == 0:
            robust_coeff = {}
            
            for target in self.db.get_targets(request.algorithm): 
            
                for hw in self.db.get_hws(request.algorithm): 
                    # The target price is not estimated: it does not require any robustness coefficient 
            
                    if target == 'price': 
                        robust_coeff[(hw, "price")] = 0
            
                    else: 
                        dataset = self.get_dataset(request.algorithm, hw)
                        model = models.get_model(request.algorithm, hw, target)

                        #ml_inputs = [col for col in dataset.columns if col not in self.db.get_targets(request.algorithm)]
                        ml_inputs = self.expander.get_expanded_ml_input_vars(request.algorithm)
                        dataset[f'{target}_pred'] = model.predict(dataset[ml_inputs])
                        dataset[f'{target}_error'] = (dataset[f'{target}'] - dataset[f'{target}_pred']).abs()
                        robust_coeff[(hw, target)] = dataset[f'{target}_error'].std() * dataset[f'{target}_error'].quantile(request.robustness_fact)
            
            return robust_coeff
        
        else:
            return None 



class DatasetsLocal(Datasets):
    """Handles datasets stored locally."""
    
    def __init__(self, db: ConfigDB, data_path: str, categories_path: str):
        super().__init__(db, categories_path)
        self.data_path = data_path


    def get_raw_dataset(self, algorithm: str, hw: str) -> pd.DataFrame:
        
        dataset_path = os.path.join(self.data_path, f'{algorithm}_{hw}.csv')
        
        if not os.path.exists(dataset_path):
            raise FileNotFoundError(f'Dataset for ({algorithm}, {hw}) not found.')

        try:
            dataset = pd.read_csv(dataset_path)
        except Exception as e:
            raise ValueError(f"Failed to read dataset CSV ({dataset_path}): {e}")

        # checking if data complies to configs
        self._check_dataset_consistency(dataset, algorithm, hw)

        return dataset


    def get_dataset(self, algorithm, hw):

        dataset = self.get_raw_dataset(algorithm, hw)
        # expanding str variables into bin (one-hot encoding) internally
        dataset = self.expander._expand_categoricals(dataset, algorithm)

        return dataset



class DatasetsRemote(Datasets):
    """Handles retrieval of datasets from the storage web service."""
    
    def __init__(self, db: ConfigDB, address: str, categories_path):
        super().__init__(db, categories_path)
        self.address = address


    def get_raw_dataset(self, algorithm: str, hw: str):
        
        dataset_url = urljoin(self.address, f'/datasets/{algorithm}/{hw}/input')

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


    def get_dataset(self, algorithm, hw):
        
        dataset = self.get_raw_dataset(algorithm, hw)
        # expanding str variables into bin (one-hot encoding) internally
        dataset = self.expander._expand_categoricals(dataset, algorithm)

        return dataset



class StrExpander():
    """Class that handles expansion of str variables via one-hot encoding."""
    """Only one versione, with input, to be consistent with logic rules."""

    
    def __init__(self, datasets: Datasets, categories_path: str):
        """
        Args:
            datasets: Datasets instance.
            categories_path (str): base directory where category mappings are stored.
        """
        self.datasets = datasets
        # path where the categories for "str" variables (categoricals) are stored
        self.categories_path = categories_path


    ### UTILITY METHODS ###

    def _get_categories_path(self, algorithm: str) -> str:
        """Returns path for the categories relative to an algorithm (pickle)."""
        return os.path.join(self.categories_path, f"{algorithm}.pkl")


    def _get_onehot_var_name(self, var_name: str, category: str) -> str:
        """Return the name of a one-hot encoded variable."""
        return f"{var_name}_{category}"


    def get_category_from_onehot(category: str, onehot_var_name: str) -> str:
        """Extracts category values from a one-hot encoded column."""
        return onehot_var_name.split(f'{category}_')[-1]


    ### EXPANSION LOGIC ###

    def get_expanded_hyperparams(self, algorithm: str) -> list:
        """
        Return list of new hyperparams, where str variables are one-hot encoded.
        """
        og_hyperparams = self.datasets.db.get_hyperparams(algorithm)
        str_vars = self.datasets.db.get_str_vars(algorithm)

        # some hyperparameters need to be expandend, others need to be kept as is (general case)
        non_expanded = [hp for hp in og_hyperparams if hp not in str_vars]
        to_expand = [hp for hp in og_hyperparams if hp in str_vars]
        
        # hyperparameters that have to be expanded
        expanded_vars_per_str_var = self.get_expanded_vars_per_str_var(algorithm)
        expanded = [v for hp in to_expand for v in expanded_vars_per_str_var[hp]]

        return non_expanded + expanded


    def get_expanded_inputs(self, algorithm: str) -> list:
        """
        Return list of new inputs, where str variables are one-hot encoded.
        """
        og_inputs = self.datasets.db.get_inputs(algorithm)
        str_vars = self.datasets.db.get_str_vars(algorithm)

        # some inputs need to be expandend, others need to be kept as is (general case)
        non_expanded = [i for i in og_inputs if i not in str_vars]
        to_expand = [i for i in og_inputs if i in str_vars]
        
        # inputs that have to be expanded
        expanded_vars = self.get_expanded_vars_per_str_var(algorithm)
        expanded = [v for i in to_expand for v in expanded_vars[i]]

        return non_expanded + expanded


    def get_expanded_ml_input_vars(self, algorithm: str) -> list:
        """
        Return list of features to be fed to ML models (hypeparameters and inputs), where str variables are one-hot encoded.
        """
        expanded_hyperparams = self.get_expanded_hyperparams(algorithm)
        expanded_inputs = self.get_expanded_inputs(algorithm)
        
        return expanded_hyperparams + expanded_inputs


    def get_expanded_var_type(self, algorithm: str) -> dict:
        """
        Return list of new var_type, where str variables are one-hot encoded.
        """
        og_var_type = self.datasets.db.get_type_per_var(algorithm)
        str_vars = self.datasets.db.get_str_vars(algorithm)

        expanded_var_type = {var : og_var_type[var] for var in og_var_type if var not in str_vars}
        expanded_vars_per_str_var = self.get_expanded_vars_per_str_var(algorithm)
        
        for str_var in str_vars:
            expanded_var_type.update({category : 'bin' for category in expanded_vars_per_str_var[str_var]})

        return expanded_var_type


    def get_categories_per_str_var(self, algorithm: str) -> dict:
        """
        Return dictionary with str variables as keys and the correspong set of unique values as values.
        Makes use of get_dataset to create create the file containing the categories, if it does not exist.

        Args:
            algorithm (str): algorithm for which we want to know the categorical variables and the corresponding categories.

        Returns:
            dict[str, set]: dictionary with str variables as keys and the corresponding set of unique values as values.

        """
        algo_categories_path = self._get_categories_path(algorithm)
        
        if not os.path.exists(algo_categories_path):
            # get_datasets() creates the categories pickle if it does not exist
            first_hw = self.datasets.db.get_hws(algorithm, )[0]
            _ = self.datasets.get_dataset(algorithm, first_hw)

        with open(algo_categories_path, "rb") as f:
            return pickle.load(f)


    def get_expanded_vars_per_str_var(self, algorithm: str) -> dict:
        """
        Return dictionary with str variables as keys and the correspong set of new variables as values.

        Args:
            algorithm (str): algorithm for which we want to know the categorical variables and the corresponding categories.

        Returns:
            dict: dictionary with str variables as keys and the corresponding set of new variables as values.

        """
        categories = self.get_categories_per_str_var(algorithm)
        
        return {
            var: [self._get_onehot_var_name(var, category) for category in cats]
                for var, cats in categories.items()
            }


    def get_encoded_selection(self, algorithm: str, var: str, selected_category: str) -> dict:
        """
        Return dict with encoded variables (for a given categorical var.) as keys, with value being 1 for the selected category, 0 for the rest.
        """
        categories = self.get_categories_per_str_var(algorithm)
        encoded_values = {}
        
        for category in categories[var]:
            value = 1 if category == selected_category else 0
            encoded_values[self._get_onehot_var_name(var, category)] = value
        
        return encoded_values


    def _expand_categoricals(self, df: pd.DataFrame, algorithm: str) -> pd.DataFrame:
        """
        Expands categorical variables (type "str") to one-hot encoding (type "bin") internally.
        The mapping is stored on disk if not already existing, and is common for all hardwares for a given algorithm; 
        Assumption: if new hardware platforms are added for a given algorithm, they must have no new categories for the str variables;
        otherwise the mappings have to be invalidated manually.

        Args:
            df (pd.DataFrame): dataset about a specific algorithm and hardware.
            algorithm (str): the algorithm which categoricals have to be handled.
            checked (bool): whether the datasets have been already checked since init (the operation is needed just once).

        Returns:
            pd.DataFrame: DataFrame with str variables being one-hot encoded.
        """
        path = self._get_categories_path(algorithm)

        # load mapping (if existing) otherwise make it (based on current dataset) and store it
        if os.path.exists(path):
            with open(path, "rb") as f:
                categories = pickle.load(f)
        
        else:
            # get all str variables for all hw
            str_vars = self.datasets.db.get_str_vars(algorithm)

            # get all unique values from various hw datasets, to create global mapping for the algorithm
            # get categories for all current hardware platforms
            categories = defaultdict(set)
            hws = self.datasets.db.get_hws(algorithm)
            
            for hw in hws:
                df_hw = self.datasets.get_raw_dataset(algorithm, hw)
                for var in str_vars:
                        new_values = set(df_hw[var].dropna().unique().tolist())
                        categories[var] = categories[var].union(new_values)
            
            with open(path, "wb") as f:
                pickle.dump(categories, f)

        # expanding variables
        for var, var_categories in categories.items():
            if not set(df[var].unique().tolist()).issubset(var_categories):
                raise AttributeError(f"Found unexpected categories for algorithm {algorithm}")
            
            # adding all categories (for all harware platforms), even if not present in this specific dataset
            df[var] = pd.Categorical(df[var], categories=var_categories)
            dummies = pd.get_dummies(df[var], prefix=var, prefix_sep="_")
            df = pd.concat([df.drop(columns=[var]), dummies], axis=1)

        return df
