import os
import requests
import pickle
from abc import ABC, abstractmethod
from collections import defaultdict
from io import StringIO
from urllib.parse import urljoin
import numpy as np
import pandas as pd
from vemm.core.optimization_request import OptimizationRequest


class Datasets(ABC):
    """Class that handles all the operations on the datasets."""
    @abstractmethod
    def __init__(self, db, categories_path_no_inp, categories_path_inp):
        self.db = db 
        # handles expansion of str hyperparameters (one-hot encoding)
        self.expander = StrExpander(self, categories_path_no_inp, categories_path_inp)

    @classmethod
    def from_local(cls, db, data_path_no_inp, data_path_inp, categories_path_no_inp, categories_path_inp):
        """Initialize Datasets using local datasets.

        Args:
            db (ConfigDB): instance of ConfigDB.
            data_path_no_inp (str): local path containing the datasets (non input-dependent case).
            data_path_inp (str): local path containing the datasets (input-dependent case).

        Returns:
            Datasets: instance of Datasets.
        """
        return DatasetsLocal(db, data_path_no_inp, data_path_inp, categories_path_no_inp, categories_path_inp)

    @classmethod
    def from_remote(cls, db, address, categories_path_no_inp, categories_path_inp):
        """Initialize Datasets using remote datasets (VM storage ervice).

        Args:
            db (ConfigDB): instance of ConfigDB.
            address (str): complete URL relative to the service that handles the datasets.

        Returns:
            Datasets: instance of Datasets.
        """
        return DatasetsRemote(db, address, categories_path_no_inp, categories_path_inp)

    @abstractmethod
    def get_raw_dataset(self, algorithm, hw, input_dependent) -> pd.DataFrame:
        """Returns the dataset (Pandas DataFrame) relative to the (algorithm, hw), if present. No categorical expansion."""
        pass

    @abstractmethod
    def get_dataset(self, algorithm, hw, input_dependent) -> pd.DataFrame:
        """Returns the dataset (Pandas DataFrame) relative to the (algorithm, hw), if present. Includes categorical expansion."""
        pass

    def _check_dataset_consistency(self, df, algorithm, hw, input_dependent=False):
        """Checking the columns are the expected ones and that they are numericals."""
        hyperparams = self.db.get_hyperparams(algorithm, input_dependent)
        data_targets = self.db.get_targets(algorithm, input_dependent)
        data_targets.remove('price')
        if input_dependent:
            inputs = self.db.get_inputs(algorithm)

        expected_columns = hyperparams + data_targets
        if input_dependent:
            expected_columns.extend(inputs)
        if set(df.columns) != set(expected_columns):
            raise AttributeError(f'Columns in the dataset for algorithm {algorithm} and hardware {hw} are not the expected ones.')
         
        #from pandas.api.types import is_numeric_dtype
        type_per_var = self.db.get_type_per_var(algorithm, input_dependent)
        numerical_vars = [var for var in type_per_var if var not in self.db.get_str_vars(algorithm, input_dependent)]
        for column in df.columns:
            if column in numerical_vars and not pd.api.types.is_numeric_dtype(df[column]):
                raise AttributeError(f'Column {column} in the dataset for algorithm {algorithm} and hardware {hw} is not numeric.')

            # checking consistency with vartype declared in configs: int, float or bin
            # float already checked: if it's numerical it can be interpreted as float
            expected_dtype = type_per_var[column]
            if expected_dtype == 'int' and not pd.api.types.is_integer_dtype(df[column]):
                raise ValueError(f'Column {column} in the dataset for algorithm {algorithm} and hardware {hw} is expected to be integer, but has non-integer values.')
            elif expected_dtype == 'bin' and set(df[column].unique()) != {0, 1}:
                raise ValueError(f'Column {column} in the dataset for algorithm {algorithm} and hardware {hw} is expected to be binary, but has non-binary values.')

    def extract_var_bounds(self, algorithm, input_dependent=False):
        """
        Compute upper and lower bounds of each variable.
        If UB/LB specified in configs, use that instead of extracting from data.

        Args:
            algorithm (str): algorithm for which we want to extract variable bounds.
            input_dependent (bool): input case (True for input-dependent, False for input_independent).

        Returns:
            lb_per_var (dict): lower bound for each variable (hyperparameters and targets; inputs too for the input-dependent cases).
            ub_per_var (dict): upper bound for each variable (hyperparameters and targets; inputs too for the input-dependent cases).
        """
        # check if both UB and LB are specified in the configs
        # otherwise add to "missing_bounds"; if any extract from data and calculate those

        # retrieving LBs/UBs from configs
        lb_per_var = self.db.get_lb_per_var(algorithm, input_dependent)
        ub_per_var = self.db.get_ub_per_var(algorithm, input_dependent)

        str_vars = self.db.get_str_vars(algorithm, input_dependent)
        # handling non-specified bounds by extracting them from data; skipping str variables
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

            for hw in self.db.get_hws(algorithm, input_dependent):
            
                dataset = self.get_dataset(algorithm, hw, input_dependent)

                for var in lb_missing_vars:
                    all_mins_per_var[var].append(dataset[var].min())
                for var in ub_missing_vars:
                    all_maxes_per_var[var].append(dataset[var].max())

            for var in lb_missing_vars:
                lb_per_var[var] = min(all_mins_per_var[var]).item()
            for var in ub_missing_vars:
                ub_per_var[var] = max(all_maxes_per_var[var]).item()

            # checking that dtypes of variables are compatible with the bounds
            type_per_var = self.db.get_type_per_var(algorithm, input_dependent)
            for var, dtype in type_per_var.items():
                var_lb = lb_per_var[var]
                var_ub = ub_per_var[var]
                if dtype == 'int':
                    if type(var_lb) is not int or type(var_ub) is not int:
                        raise ValueError(f'Bound for variable {var} is not of the expected type (int).')
                elif dtype == 'bin':
                    if (var_lb not in [0,1]) or (var_ub not in [0,1]):
                        raise ValueError(f'Bound for variable {var} is not of the expected type (bin): it must be 0 or 1.')

        return lb_per_var, ub_per_var

    def get_var_bounds_all(self, request: OptimizationRequest):
        """
        Compute upper and lower bounds of each variable, including price.
        If UB/LB specified in configs, use that instead of extracting from data.
        Handles "price" on top of the regular targets.

        Args:
            request (OptimizationRequest): instance of OptimizationRequest.

        Returns:
            var_bounds (dict): lower bound and upper bound for each variable, including price.
        """
        lb_per_var, ub_per_var = self.extract_var_bounds(request.algorithm, request.input_dependent)

        if request.target == 'price' or 'price' in request.user_constraints.get_constraints():
            lb_per_var['price'] = min(request.hws_prices.get_prices_per_hw().values())
            ub_per_var['price'] = max(request.hws_prices.get_prices_per_hw().values())

        var_bounds = {var: {'lb':lb_per_var[var], 'ub':ub_per_var[var]}
                        for var in lb_per_var}
        return var_bounds
        
    def get_robust_coeff(self, models, request):
        """
        Compute robustness coefficients for each predictive model, according to the specified robustness factor.

        Args:
            models (MLModels): object that handles ML models.
            request (OptimizationRequest): represents the user's request.

        Returns:
            robust_coeff (dict): robustness coefficient for each predictive model.
        """

        if request.robustness_fact or request.robustness_fact == 0:
            robust_coeff = {}
            for target in self.db.get_targets(request.algorithm, request.input_dependent): 
                for hw in self.db.get_hws(request.algorithm, request.input_dependent): 
                    # The target price is not estimated: it does not require any robustness coefficient 
                    if target == 'price': 
                        robust_coeff[(hw, "price")] = 0
                    else: 
                        dataset = self.get_dataset(request.algorithm, hw, request.input_dependent)
                        model = models.get_model(request.algorithm, hw, target, request.input_dependent)

                        #ml_inputs = [col for col in dataset.columns if col not in self.db.get_targets(request.algorithm)]
                        ml_inputs = self.expander.get_expanded_ml_input_vars(request.algorithm, request.input_dependent)
                        dataset[f'{target}_pred'] = model.predict(dataset[ml_inputs])
                        dataset[f'{target}_error'] = (dataset[f'{target}'] - dataset[f'{target}_pred']).abs()
                        robust_coeff[(hw, target)] = dataset[f'{target}_error'].std() * dataset[f'{target}_error'].quantile(request.robustness_fact)
            return robust_coeff
        else:
            return None 


class DatasetsLocal(Datasets):
    """Handles datasets stored locally."""
    def __init__(self, db, data_path_no_inp, data_path_inp, categories_path_no_inp, categories_path_inp):
        super().__init__(db, categories_path_no_inp, categories_path_inp)
        self.data_path_no_inp = data_path_no_inp
        self.data_path_inp = data_path_inp

    def get_raw_dataset(self, algorithm, hw, input_dependent=False):
        path = self.data_path_inp if input_dependent else self.data_path_no_inp
        dataset_path = os.path.join(path, f'{algorithm}_{hw}.csv')
        if not os.path.exists(dataset_path):
            raise FileNotFoundError(f'Dataset for ({algorithm}, {hw}) not found.')

        dataset = pd.read_csv(dataset_path)

        # checking if data complies to configs
        self._check_dataset_consistency(dataset, algorithm, hw, input_dependent)

        return dataset

    def get_dataset(self, algorithm, hw, input_dependent=False):

        dataset = self.get_raw_dataset(algorithm, hw, input_dependent)
        # expanding str variables into bin (one-hot encoding) internally
        dataset = self.expander._expand_categoricals(dataset, algorithm, input_dependent)

        return dataset

class DatasetsRemote(Datasets):
    """Handles retrieval of datasets from the storage web service."""
    def __init__(self, db, address, categories_path_no_inp, categories_path_inp):
        super().__init__(db, categories_path_no_inp, categories_path_inp)
        self.address = address

    def get_raw_dataset(self, algorithm, hw, input_dependent=False):
        request_url = f'/datasets/{algorithm}/{hw}'
        if input_dependent:
            request_url += '/input'
        algo_hw_url = urljoin(self.address, request_url)
        req = requests.request('GET', algo_hw_url)
        if req.status_code != 200:
            raise FileNotFoundError(f'Dataset for ({algorithm}, {hw}) not found.')
        csv_file = req.content

        dataset = pd.read_csv(StringIO(csv_file.decode('utf-8')))

        # checking if data complies to configs
        self._check_dataset_consistency(dataset, algorithm, hw, input_dependent)

        return dataset

    def get_dataset(self, algorithm, hw, input_dependent=False):
        
        dataset = self.get_raw_dataset(algorithm, hw, input_dependent)
        # expanding str variables into bin (one-hot encoding) internally
        dataset = self.expander._expand_categoricals(dataset, algorithm, input_dependent)

        return dataset


class StrExpander():
    """Class that handles expansion of str variables via one-hot encoding."""
    def __init__(self, datasets, categories_path_no_inp, categories_path_inp):
        self.datasets = datasets
        # path where the categories for "str" variables (categoricals) are stored
        self.categories_path_no_inp = categories_path_no_inp
        self.categories_path_inp = categories_path_inp

    def _get_categories_path(self, algorithm, input_dependent=False):
        """Returns path for the categories relative to an algorithm (pickle)."""
        path = self.categories_path_inp if input_dependent else self.categories_path_no_inp
        return os.path.join(path, f'{algorithm}.pkl')

    def _get_onehot_var_name(self, og_var_name, category):
        """Get name of a new (expanded) one-hot column."""
        return og_var_name + '_' + str(category)

    def get_category_from_onehot(category, onehot_var_name):
        """Extracts category values from a one-hot encoded column."""
        return onehot_var_name.split(f'{category}_')[-1]

    def get_expanded_hyperparams(self, algorithm, input_dependent=False):
        """Return list of new hyperparams, where str variables are one-hot encoded."""
        og_hyperparams = self.datasets.db.get_hyperparams(algorithm, input_dependent)
        str_vars = self.datasets.db.get_str_vars(algorithm, input_dependent)

        # some hyperparameters need to be expandend, others need to be kept as is (general case)
        non_ext_hyperparams = [hyperparam for hyperparam in og_hyperparams if hyperparam not in str_vars]
        hyperparams_to_extend = [hyperparam for hyperparam in og_hyperparams if hyperparam in str_vars]
        # hyperparameters that have to be expanded
        expanded_vars_per_str_var = self.get_expanded_vars_per_str_var(algorithm, input_dependent)
        ext_hyperparams = []
        for ext_hyperparam in hyperparams_to_extend:
            ext_hyperparams.extend(expanded_vars_per_str_var[ext_hyperparam])

        return non_ext_hyperparams + ext_hyperparams

    def get_expanded_inputs(self, algorithm, input_dependent=False):
        """Return list of new inputs, where str variables are one-hot encoded."""
        og_inputs = self.datasets.db.get_inputs(algorithm)
        str_vars = self.datasets.db.get_str_vars(algorithm, input_dependent)

        # some inputs need to be expandend, others need to be kept as is (general case)
        non_ext_inputs = [input for input in og_inputs if input not in str_vars]
        inputs_to_extend = [input for input in og_inputs if input in str_vars]
        # inputs that have to be expanded
        expanded_vars_per_str_var = self.get_expanded_vars_per_str_var(algorithm, input_dependent)
        ext_inputs = []
        for ext_input in inputs_to_extend:
            ext_inputs.extend(expanded_vars_per_str_var[ext_input])

        return non_ext_inputs + ext_inputs

    def get_expanded_ml_input_vars(self, algorithm, input_dependent=False):
        """Return list of features to be fed to ML models (hypeparameters and inputs), where str variables are one-hot encoded."""
        expanded_hyperparams = self.get_expanded_hyperparams(algorithm, input_dependent)

        if input_dependent:
            #return expanded_hyperparams + self.datasets.db.get_inputs(algorithm, input_dependent)
            expanded_inputs = self.get_expanded_inputs(algorithm, input_dependent)
            return expanded_hyperparams + expanded_inputs
        else:
            return expanded_hyperparams

    def get_expanded_var_type(self, algorithm, input_dependent):
        """Return list of new var_type, where str variables are one-hot encoded."""
        og_var_type = self.datasets.db.get_type_per_var(algorithm, input_dependent)
        str_vars = self.datasets.db.get_str_vars(algorithm, input_dependent)

        expanded_var_type = {var : og_var_type[var] for var in og_var_type if var not in str_vars}
        expanded_vars_per_str_var = self.get_expanded_vars_per_str_var(algorithm, input_dependent)
        for str_var in str_vars:
            expanded_var_type.update({category : 'bin' for category in expanded_vars_per_str_var[str_var]})

        return expanded_var_type

    def get_categories_per_str_var(self, algorithm, input_dependent=False):
        """
        Return dictionary with str variables as keys and the correspong set of unique values as values.
        Makes use of get_dataset to create create the file containing the categories, if it does not exist.

        Args:
            algorithm (str): algorithm for which we want to know the categorical variables and the corresponding categories.

        Returns:
            dict: dictionary with str variables as keys and the corresponding set of unique values as values.

        """
        algo_categories_path = self._get_categories_path(algorithm, input_dependent)
        if not os.path.exists(algo_categories_path):
            # get_datasets() creates the categories pickle if it does not exist
            first_hw = self.datasets.db.get_hws(algorithm, input_dependent)[0]
            _ = self.datasets.get_dataset(algorithm, first_hw, input_dependent)

        categories = pickle.load(open(algo_categories_path, 'rb'))
        return categories

    def get_expanded_vars_per_str_var(self, algorithm, input_dependent=False):
        """
        Return dictionary with str variables as keys and the correspong set of new variables as values.

        Args:
            algorithm (str): algorithm for which we want to know the categorical variables and the corresponding categories.

        Returns:
            dict: dictionary with str variables as keys and the corresponding set of new variables as values.

        """
        categories = self.get_categories_per_str_var(algorithm, input_dependent)
        return {var:[self._get_onehot_var_name(var, category) for category in var_categories]
                for var, var_categories in categories.items()}

    def get_encoded_selection(self, algorithm, var, selected_category, input_dependent=False):
        """Return dict with encoded variables (for a given categorical var.) as keys, with value being 1 for the selected category, 0 for the rest."""
        categories = self.get_categories_per_str_var(algorithm, input_dependent)
        encoded_values = {}
        for category in categories[var]:
            value = 1 if category == selected_category else 0
            encoded_values[self._get_onehot_var_name(var, category)] = value
        
        return encoded_values


    def _expand_categoricals(self, df, algorithm, input_dependent=False):
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

        # load mapping (if existing) otherwise make it (based on current dataset) and store it
        algo_categories_path = self._get_categories_path(algorithm, input_dependent)
        if os.path.exists(algo_categories_path):
            categories = pickle.load(open(algo_categories_path, 'rb'))
        else:
            # get all str variables for all hw
            str_vars = self.datasets.db.get_str_vars(algorithm, input_dependent)

            # get all unique values from various hw datasets, to create global mapping for the algorithm
            # get categories for all current hardware platforms
            categories = defaultdict(set)
            hws = self.datasets.db.get_hws(algorithm, input_dependent)
            for hw in hws:
                df_hw = self.datasets.get_raw_dataset(algorithm, hw, input_dependent)
                for var in str_vars:
                        new_values = set(df_hw[var].dropna().unique().tolist())
                        categories[var] = categories[var].union(new_values)
            
            pickle.dump(categories, open(algo_categories_path, 'wb'))

        # expanding variables
        for var, var_categories in categories.items():
            if not set(df[var].unique().tolist()).issubset(var_categories):
                raise AttributeError(f"Found unexpected categories for algorithm {algorithm}")
            
            # adding all categories (for all harware platforms), even if not present in this specific dataset
            df[var] = pd.Categorical(df[var], categories=var_categories)
            new_cols = pd.get_dummies(df[var], prefix=var, prefix_sep='_')
            df.drop(var, axis=1, inplace=True)
            df = pd.concat([df,new_cols], axis=1)

        return df
