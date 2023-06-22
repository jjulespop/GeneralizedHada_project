import pandas as pd
import os

data = pd.read_csv('algorithms/data/bca.csv')

for task in data['AI_TASK'].unique():
    for platform in data['PLATFORM'].unique():

        #generate configs
        os.system(f"cp algorithms/configs/bca_template.json algorithms/configs/{task}_{platform}.json")
        os.system(f"sed -i '' '2s/REPLACE-WITH-TASK/{task}/' algorithms/configs/{task}_{platform}.json")
        os.system(f"sed -i '' '3s/REPLACE-WITH-PLATFORM/{platform}/' algorithms/configs/{task}_{platform}.json")

        #create data
        df = data.loc[(data['AI_TASK'] == task) & (data['PLATFORM'] == platform)]
        df = df.drop(['AI_TASK', 'PLATFORM', 'NOTES', 'UPDATED BY', 'LAST UPDATE'], axis = 1)
        df.to_csv(f'algorithms/data/{task}_{platform}.csv', index = False)
