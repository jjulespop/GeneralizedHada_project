'''
Class that handles operations that have to be carried out on the ML models.
'''
import os
import pickle
import time
from multiprocessing import Process, Manager
from sklearn.tree import DecisionTreeRegressor

class MLModels():
    def __init__(self, db, datasets, models_path_no_inp, models_path_inp):
        """Handles all operations on ML models.

        Args:
            db (ConfigDB): ConfigDB instance.
            datasets (Datasets): Datasets instance.
            models_path_no_inp (str): local path containing the models (non input-dependent case).
            models_path_inp (str): local path containing the models (input-dependent case).
        """
        self.db = db
        self.models_path_no_inp = models_path_no_inp
        self.models_path_inp = models_path_inp
        self.datasets = datasets

        # tracking state about (algorithm, hw, target) that are currently being trained
        self.ongoing_training = Manager().dict()

    def __get_model_path(self, algorithm, hw, target, input_dependent=False):
        path = self.models_path_inp if input_dependent else self.models_path_no_inp
        return os.path.join(path, f'{algorithm}_{hw}_{target}_DecisionTree_10')

    def get_model(self, algorithm, hw, target, input_dependent=False):
        """Returns the model (Decision).

        Args:
            algorithm (str): algorithm id.
            hw (str): hardware platform id
            target (str): target id.
            input_dependent (bool): input case (True for input-dependent, False for input_independent).

        Raises:
            Exception: if model is not found and is already being trained.

        Returns:
            sklearn.tree.DecisionTreeRegressor: DT model.
        """
        model_path = self.__get_model_path(algorithm, hw, target, input_dependent) 

        if not os.path.exists(model_path):
            if (algorithm, hw, target, input_dependent) in self.ongoing_training:
                raise Exception(f'Model for ({algorithm}, {hw}, {target}) training is ongoing. Come back later.')
            else:
                # launching training in background
                dataset = self.datasets.get_dataset(algorithm, hw, input_dependent)
                self.ongoing_training[(algorithm, hw, target, input_dependent)] = True
                p = Process(target=self.__run_training, args=(algorithm, 
                                                              hw,
                                                              target,
                                                              dataset,
                                                              input_dependent))
                p.start()
                #raise FileNotFoundError(f'Model for ({algorithm}, {hw}, {target}) does not exist. Training started. Come back later.')
                # without the Exception, nothing is shown in the GUI, but multiple models can be trained in a single
                # request, while still keeping all the training part incapsulated in "get_model"
                print(f'Model for ({algorithm}, {hw}, {target}) does not exist. Training started.')
                p.join()
                del self.ongoing_training[(algorithm, hw, target, input_dependent)]
                print(f'Finished training model for ({algorithm}, {hw}, {target}).')


        # model exists, load it
        model = pickle.load(open(model_path, 'rb'))
        return model

    def __run_training(self, algorithm, hw, target, dataset, input_dependent=False):
        """
        Trains a Decision Tree and stores it with pickle.

        Args:
            algorithm (str): algorithm id.
            hw (str): hardware platform id.
            target (str): target id.
            dataset (pd.DataFrame): training dataset.
            input_dependent (bool): input case (True for input-dependent, False for input_independent).
        
        """
        #s = time.time()
        model_path = self.__get_model_path(algorithm, hw, target, input_dependent)

        # filtering dataset for the specific hyperparams and target
        #hyperparams = self.db.get_hyperparams(algorithm)
        # handling str variables, substituting them with one-hot encoded ones
        input_vars = self.datasets.expander.get_expanded_ml_input_vars(algorithm, input_dependent)
        X = dataset[input_vars].values
        y = dataset[[target]].values

        # training the DT
        dt = DecisionTreeRegressor(max_depth=10, random_state=42)
        #dt = DecisionTreeRegressor(max_depth=None, random_state=42)
        dt.fit(X, y)

        # storing the DT
        pickle.dump(dt, open(model_path, 'wb'))

        #print(self.ongoing_training)
        #print(f'Done in {time.time()-s}')
        #del self.ongoing_training[(algorithm, hw, target)]
        #print(self.ongoing_training)
