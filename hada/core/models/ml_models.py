'''
Class that handles operations that have to be carried out on the ML models.
'''
import os
import pickle
import time
import pandas as pd
from multiprocessing import Process, Manager
from sklearn.tree import DecisionTreeRegressor
from hada.core.config.configdb import ConfigDB
from hada.core.config.datasets import Datasets




class MLModels():


    def __init__(self, db: ConfigDB, datasets: Datasets, models_path: str):
        """
        Initialize the MLModels and handle all operations.

        Args:
            db (ConfigDB): ConfigDB instance.
            datasets (Datasets): Datasets instance.
            models_path (str): directory where trained models are stored.
        """

        self.db = db
        self.models_path = models_path
        self.datasets = datasets

        # tracks currently training models to avoid redundant runs
        self.ongoing_training = Manager().dict()


    def _get_model_path(self, algorithm: str, hw: str, target: str) -> str:
        """Return the file path for the given model."""
        return os.path.join(self.models_path, f'{algorithm}_{hw}_{target}_DecisionTree_10')


    def get_model(self, algorithm: str, hw: str, target: str) -> DecisionTreeRegressor:
        """
        Retrieve a trained model. If it doesn't exist, starts new training.

        Args:
            algorithm (str): algorithm identifier.
            hw (str): hardware platform identifier.
            target (str): target variable name.

        Raises:
            RuntimeError: if a model is not found or is alredy being trained.

        Returns:
            DecisionTreeRegressor: trained Decision Tree model.
        """

        model_path = self._get_model_path(algorithm, hw, target) 

        # case 1: model already exists - load and return it
        if os.path.exists(model_path):
            with open(model_path, "rb") as f:
                return pickle.load(f)

        # case 2: model is being trained elsewhere
        if (algorithm, hw, target) in self.ongoing_training:
            raise RuntimeError(f"Training already in progress for ({algorithm}, {hw}, {target}). Please retry later.")

        # case 3: model not found - start training
        self.ongoing_training[(algorithm, hw, target)] = True
        dataset = self.datasets.get_dataset(algorithm, hw)
        self._train_and_save_model(algorithm, hw, target, dataset)
        del self.ongoing_training[(algorithm, hw, target)]
        print(f'Finished training model for ({algorithm}, {hw}, {target}).')

        # load the newly trained model
        with open(model_path, "rb") as f:
            return pickle.load(f)



    def _train_and_save_model(self, algorithm: str, hw: str, target: str, dataset: pd.DataFrame):
        """
        Train a Decision Tree model and save it to disk with pickle.

        Args:
            algorithm (str): algorithm identifier.
            hw (str): hardware platform identifier.
            target (str): target variable name.
            dataset (pd.DataFrame): training dataset.
        """

        #s = time.time()
        model_path = self._get_model_path(algorithm, hw, target)

        # extract relevant columns for training
        hyperparams = self.db.get_hyperparams(algorithm)
        input_vars = self.db.get_inputs(algorithm)
        X = dataset[hyperparams + input_vars].values
        y = dataset[[target]].values

        # training the DT
        model = DecisionTreeRegressor(max_depth=10, random_state=42)
        model.fit(X, y)

        # storing the DT
        with open(model_path, "wb") as f:
            pickle.dump(model, f)
