'''
Class that handles operations that have to be carried out on the ML models.
'''
import os
import pickle
import time
from multiprocessing import Process, Manager

class MLModels():
    def __init__(self, db, models_path):
        self.db = db
        self.models_path = models_path

        # tracking state about (algorithm, hw, target) that are currently being trained
        self.ongoing_training = Manager().dict()

    def __get_model_path(self, algorithm, hw, target):
        return os.path.join(self.models_path, f'{algorithm}_{hw}_{target}_DecisionTree_10')

    def get_model(self, algorithm, hw, target):
        model_path = self.__get_model_path(algorithm, hw, target) 

        if not os.path.exists(model_path):
            if (algorithm, hw, target) in self.ongoing_training:
                raise Exception(f'Model for ({algorithm}, {hw}, {target}) training is ongoing. Come back later.')
            else:
                self.ongoing_training[(algorithm, hw, target)] = True
                # launching training in background
                p = Process(target=self.__run_training, args=(algorithm, 
                                                              hw,
                                                              target))
                p.start()
                raise FileNotFoundError(f'Model for ({algorithm}, {hw}, {target}) does not exist. Training started. Come back later.')

        # model exists, load it
        model = pickle.load(open(model_path, 'rb'))
        return model

    def __run_training(self, algorithm, hw, target):
        '''Mock function. Training to be implemented. It also updates shared state about models that are being trained.'''
        model_path = self.__get_model_path(algorithm, hw, target)

        # mock training
        time.sleep(15)
        pickle.dump({'test':1}, open(model_path, 'wb'))

        print(f'Finished training model for ({algorithm}, {hw}, {target}).')
        #print(ongoing_training)
        del self.ongoing_training[(algorithm, hw, target)]
        #print(ongoing_training)
