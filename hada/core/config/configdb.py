import os
import json
import requests
from urllib.parse import urljoin


class ConfigDB():
    """
    Manages configuration data for (algorithm, hardware) pairs, loaded either 
    from local JSON files or a remote service.

    Each configuration file describes one (algorithm, hardware) pair
    with hyperparameters, input variables, targets, and hardware pricing.
    """


    @classmethod
    def from_local(cls, path: str):
        """
        Create a ConfigDB instance by loading configuration files from a local directory.

        Expected filename format: '<algorithm>_<hardware>.json'

        Args:
            path (str): local directory containing JSON config files.

        Returns:
            ConfigDB: initialized instance of ConfigDB.
        """

        fnames = sorted(os.listdir(path))
        algo_hw_pairs, configs = [], []

        for fname in fnames:
            if not fname.endswith(".json"):
                continue

            algorithm, hw_part = fname.split('_', 1)
            hw = hw_part.split('.')[0]
            file_path = os.path.join(path, fname)

            with open(file_path, 'r') as f:
                config = json.load(f)

            algo_hw_pairs.append((algorithm, hw))
            configs.append(config)

        return cls(configs, algo_hw_pairs)


    @classmethod
    def from_remote(cls, base_url: str):
        """
        Create a ConfigDB instance by fetching configurations from a remote service.

        The service must expose:
            - '/configs endpoint returning a list of configs with 'algorithm' and 'hw' keys
            - '/configs/<algorithm>/<hw>' endpoint returning the full JSON configuration

        Args:
            base_url (str): base URL of the remote configuration service.

        Returns:
            ConfigDB: initialized instance of ConfigDB.
        """
        # test availability
        #requests.head(address)

        # getting list of config files
        configs_url = urljoin(base_url, '/configs')
        response = requests.get(url=configs_url)

        configs_data = response.json()['configs']
        algo_hw_pairs = [(cfg['algorithm'], cfg['hw']) for cfg in configs_data]

        configs = []
        for algorithm, hw in algo_hw_pairs:
            config_url = urljoin(base_url, f'/configs/{algorithm}/{hw}')
            config = json.loads(requests.get(url=config_url).content)
            configs.append(config)

        return cls(configs, algo_hw_pairs)


    def __init__(self, configs: list[dict], algo_hw_pairs: list[tuple[str, str]]):
        """
        Initializes ConfigDB.

        Args:
            configs (list[dict]): list of parsed configuration dictionaries.
            algo_hw_pairs (list[tuple[str, str]]): list of (algorithm, hardware) pairs corresponding to the configs, in order.

        Raises:
            AttributeError: if hyperparameters, input variables, or targets are inconsistent across hardware for the same algorithm.
        """
        
        # scan path
        #self.fnames = [os.path.join(path, fname) for fname in sorted(os.listdir(path))]

        # dictionary with the name of algorithms as keys and values structured like this:
        #{
        #    'hyperparams': {'var_0': {'type': 'int', 'LB': None, 'UB': None},
        #                    'var_1': {'type': 'int', 'LB': None, 'UB': None}},
        #    'targets': {'time': {'LB': None, 'UB': None},
        #                'memory': {'LB': None, 'UB': None}},
        #    'hws': {'vm': None,
        #            'pc': None, 
        #            'g100': None}

        #   "input_vars": [
        #       {"ID": "var_0", "description": null, "type": "float", "LB": null, "UB": null},
        #       {"ID": "var_1", "description": null, "type": "float", "LB": null, "UB": null},
        #   ]
        #}


        self.configs = configs
        self.algo_hw_pairs = algo_hw_pairs
        self.db = {}

        for config, (algorithm, hw) in zip(configs, algo_hw_pairs):
            
            # checking types for all fields
            self.__check_json(algorithm, hw, config)

            # extract structure info
            hyperparams = {
                hyperparam['ID']: {
                    'type': hyperparam['type'],
                    'description': hyperparam['description'],
                    'LB': hyperparam['LB'],
                    'UB': hyperparam['UB']
                }
                for hyperparam in config['hyperparams']}

            input_vars = {
                input_var['ID']: {
                    'type': input_var['type'],
                    'description': input_var['description'],
                    'LB': input_var['LB'],
                    'UB': input_var['UB']
                }
                for input_var in config['input_vars']}

            #'type': target['type'],
            targets = {
                target['ID']: {
                    'description': target['description'],
                    'LB': target['LB'],
                    'UB': target['UB']
                }
                for target in config['targets']}


            # checking for overlap of names among hyperparams and targets
            if set.intersection(set(hyperparams), set(targets)):
                    raise AttributeError(f'Names of hyperparams and targets must not overlap.')
            if set.intersection(set(hyperparams), set(input_vars)):
                    raise AttributeError(f'Names of hyperparams and input variables must not overlap.')
            if set.intersection(set(input_vars), set(targets)):
                    raise AttributeError(f'Names of input variables and targets must not overlap.')

            # set utility variables
            algo_name = config['name']
            hw_id = config['HW_ID']
            hw_price = config['HW_price']

            # checking consistency across hws for a given algorithm
            if algo_name not in self.db:

                self.db[algo_name] = {
                    'hyperparams': hyperparams,
                    'targets': targets,
                    'input_vars': input_vars,
                    'hws': {hw_id: hw_price}
                }
            else:

                # checking consistency of hyperparameters across hws for a given algorithm
                if self.db[algo_name]['hyperparams'] != hyperparams:
                    raise AttributeError(f'Hyperparameters not matching for algorithm {algo_name} on different hws.')
                # checking consistency of targets across hws for a given algorithm
                if self.db[algo_name]['targets'] != targets:
                    raise AttributeError(f'Targets not matching for algorithm {algo_name} on different hws.')
                # checking consistency of input variables across hws for a given algorithm
                if self.db[algo_name]['input_vars'] != input_vars:
                    raise AttributeError(f'Input variables not matching for algorithm {algo_name} on different hws.')

                # just adding the new HW and its price, the rest must be the same across hws for the given algorithm.
                self.db[algo_name]['hws'][hw_id] = hw_price


    
    ### GET METHODS ###


    def get_algorithms(self) -> list[str]:
        """Return the list of all available algorithms."""
        return list(self.db.keys())


    def get_hyperparams(self, algorithm: str) -> list[str]:
        """Return the list of hyperparameters for the given algorithm."""
        return list(self.db[algorithm]['hyperparams'].keys())


    def get_input_vars(self, algorithm: str) -> list[str]:
        """Return the list of input variables for the given algorithm."""
        return list(self.db[algorithm]['input_vars'].keys())


    def get_targets(self, algorithm: str) -> list[str]:
        """
        Return the list of targets for the given algorithm.

        The 'price' target is appended because it may be treated as a 
        special variable (defined by hardware provider rather than a model).
        """
        return list(self.db[algorithm]['targets'].keys()) + ['price']


    def get_hws(self, algorithm: str) -> list[str]:
        """Return the list of available hardware platforms for the given algorithm."""
        return list(self.db[algorithm]['hws'].keys())


    def get_prices(self, algorithm: str) -> list[float]:
        """Return the list of hardware prices for the given algorithm."""
        return list(self.db[algorithm]['hws'].values())


    def get_prices_per_hw(self, algorithm: str) -> dict[str, float]:
        """Return a mapping of (hardware ID, price) for the given algorithm."""
        return self.db[algorithm]['hws']


    def get_lb_per_var(self, algorithm: str) -> dict[str, float | None]:
        """Return the lower bounds (LB) for all variables."""

        lb = {}

        for group in ['hyperparams', 'targets', 'input_vars']:
            for var, data in self.db[algorithm][group].items():
                lb[var] = data['LB']

        return lb


    def get_ub_per_var(self, algorithm: str) -> dict[str, float | None]:
        """Return the upper bounds (UB) for all variables."""
        
        ub = {}

        for group in ['hyperparams', 'targets', 'input_vars']:
            for var, data in self.db[algorithm][group].items():
                ub[var] = data['UB']

        return ub
    

    def get_description_per_var(self, algorithm: str) -> dict[str, str | None]:
        """Return descriptions for all variables."""

        desc = {}

        for group in ['hyperparams', 'targets', 'input_vars']:
            for var, data in self.db[algorithm][group].items():
                desc[var] = data['description']

        return desc


    def get_type_per_var(self, algorithm: str) -> dict[str, str]:
        """Return types for all variables."""

        types = {}

        for var, data in self.db[algorithm]['hyperparams'].items():
            types[var] = data['type']

        for var in self.db[algorithm]['targets']:
            types[var] = 'float'

        for var, data in self.db[algorithm]['input_vars'].items():
            types[var] = data['type']

        return types


    def __check_json(self, algorithm: str, hw: str, config: dict):
        """
        Validate the structure and types of a configuration JSON entry.

        Raises:
            AttributeError: if any field is missing or has the wrong type.
        """

        try:

            # checking algorithm
            if type(config['name']) is not str:
                AttributeError('Algorithm name must be a string')

            # checking hardware
            if type(config['HW_ID']) is not str:
                AttributeError('Hardware platform name must be a string')

            if config['HW_price'] is not None and type(config['HW_price']) not in [int, float]:
                    raise AttributeError("Hardware platform price must be a number or None")


            # checking hyperparams
            for hyperparam in config['hyperparams']:

                if type(hyperparam['ID']) is not str:
                    raise AttributeError(f'ID of hyperparameters must be strings')

                if hyperparam['description'] is not None and type(hyperparam['description']) is not str:
                    raise AttributeError("Hyperparameter description must be a string")

                if hyperparam['type'] not in ['bin', 'int', 'float']:
                    raise AttributeError("Hyperparameter type must be 'bin', 'int' or 'float'")

                if hyperparam['UB'] is not None and type(hyperparam['UB']) not in [int, float]:
                    raise AttributeError("Hyperparameter upper bound must be a number or None")
                
                if hyperparam['LB'] is not None and type(hyperparam['LB']) not in [int, float]:
                    raise AttributeError("Hyperparameter lower bound must be a number or None")


            #checking input variables
            for input_var in config['input_vars']:

                if type(input_var['ID']) is not str:
                    raise AttributeError(f'ID of input variable must be strings')

                if input_var['description'] is not None and type(input_var['description']) is not str:
                    raise AttributeError("Input variable description must be a string")

                if input_var['type'] not in ['bin', 'int', 'float']:
                    raise AttributeError("Input variable type must be 'bin', 'int' or 'float'")

                if input_var['UB'] is not None and type(input_var['UB']) not in [int, float]:
                    raise AttributeError("Input variable upper bound must be a number or None")
                
                if input_var['LB'] is not None and type(input_var['LB']) not in [int, float]:
                    raise AttributeError("Input variable lower bound must be a number or None")


            # checking targets
            for target in config['targets']:

                if type(target['ID']) is not str:
                    raise AttributeError(f'ID of targets must be strings; config: ({algorithm}, {hw}')

                if target['description'] is not None and type(target['description']) is not str:
                    raise AttributeError("Target description must be a string")

                #if target['type'] not in ['bin', 'int', 'float']:
                #    raise AttributeError("Targets type must be 'bin', 'int' or 'float'")

                if target['UB'] is not None and type(target['UB']) not in [int, float]:
                    raise AttributeError("Targets upper bound must be a number or None")
                
                if target['LB'] is not None and type(target['LB']) not in [int, float]:
                    raise AttributeError("Targets lower bound must be a number or None")

        except AttributeError as e:
            print(f'Error in config ({algorithm}, {hw}): {e}')
            raise e
