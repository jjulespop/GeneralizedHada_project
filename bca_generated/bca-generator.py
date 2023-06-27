import pandas as pd
import os

targets = ['']
#data = pd.read_csv('algorithms/data/bca_generated/bca.csv')
data = pd.read_csv('bca2.csv')
generated_couples = []
excluded_couples = []

for task in data['AI_TASK'].unique():
    for platform in data['PLATFORM'].unique():
        df = data.loc[(data['AI_TASK'] == task) & (data['PLATFORM'] == platform)]
        # dropping rows with NaNs (non-valid targets)
        df = df.dropna(subset=['INFERENCE_TIME'])

        # PROBABLY THIS REASONING HAS TO BE CARRIED OUT FOR EACH TARGET (i.e. for each target at least two rows)
        # PROBABLY THIS REASONING HAS TO BE CARRIED OUT FOR EACH TARGET (i.e. for each target at least two rows)
        # PROBABLY THIS REASONING HAS TO BE CARRIED OUT FOR EACH TARGET (i.e. for each target at least two rows)
        # PROBABLY THIS REASONING HAS TO BE CARRIED OUT FOR EACH TARGET (i.e. for each target at least two rows)
        # PROBABLY THIS REASONING HAS TO BE CARRIED OUT FOR EACH TARGET (i.e. for each target at least two rows)
        # PROBABLY THIS REASONING HAS TO BE CARRIED OUT FOR EACH TARGET (i.e. for each target at least two rows)
        #if df.shape[0] < 2: # skipping datasets with just one line
        ##if df.empty:
        #    # skipping this couple, empty once the rows with invalid targets are dropped
        #    continue

        cols_to_drop = ['AI_TASK', 'PLATFORM', 'NOTES', 'UPDATED BY', 'LAST UPDATE', 'QUALITY_METRIC']

        # handling QUALITY_METRIC and QUALITY_VALUE
        metrics = df['QUALITY_METRIC'].dropna().unique()
        if metrics.shape[0] > 1:
            raise Exception('Multiple metrics here!')
        elif metrics.shape[0] == 0:
            # NaN metric and NaN value
            metric = 'null'
            cols_to_drop.extend(['QUALITY_METRIC', 'QUALITY_VALUE'])
        else:
            df['QUALITY_METRIC'] = metrics[0]
            # dropping rows with NaNs (QUALITY_VALUE)
            df = df.dropna(subset=['QUALITY_VALUE'])

        #create data
        #if df.shape[0] < 2: # skipping datasets with just one line
        # checking for each target if n_rows > 1, if not, drop rows for that target
        # checking for each target if n_rows > 1, if not, drop rows for that target
        # checking for each target if n_rows > 1, if not, drop rows for that target
        # checking for each target if n_rows > 1, if not, drop rows for that target
        # checking for each target if n_rows > 1, if not, drop rows for that target
        # checking for each target if n_rows > 1, if not, drop rows for that target
        # checking for each target if n_rows > 1, if not, drop rows for that target
        # checking for each target if n_rows > 1, if not, drop rows for that target
        # checking for each target if n_rows > 1, if not, drop rows for that target
        # checking for each target if n_rows > 1, if not, drop rows for that target
        if df.shape[0] < 2: # skipping datasets with just one line # checking for each target
            excluded_couples.append((task, platform))
            continue
        else:
            generated_couples.append((task, platform))

        df = df.drop(cols_to_drop, axis = 1)
        df.to_csv(f'../algorithms/data/input-independent/{task}_{platform}.csv', index = False)

        #generate configs
        os.system(f"cp ../bca_generated/bca_template.json ../algorithms/configs/input-independent/{task}_{platform}.json")
        os.system(f"sed -i 's/REPLACE-WITH-TASK/{task}/' ../algorithms/configs/input-independent/{task}_{platform}.json")
        os.system(f"sed -i 's/REPLACE-WITH-PLATFORM/{platform}/' ../algorithms/configs/input-independent/{task}_{platform}.json")
        if metrics.shape[0] == 0:
            os.system(f"sed -i '/QUALITY_VALUE/d' ../algorithms/configs/input-independent/{task}_{platform}.json")
        else:
            metric = f'"{metrics[0]}"'
            os.system(f"sed -i 's/REPLACE-WITH-METRIC/{metric}/' ../algorithms/configs/input-independent/{task}_{platform}.json")