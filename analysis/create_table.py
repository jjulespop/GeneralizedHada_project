'''Plots result table with training + extraction result times'''

import os
import sys
import pandas as pd
import matplotlib.pyplot as plt

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from hada.config import config_loader

config = config_loader.load_config(config_path="./hada/config/config.yaml")


if __name__ == '__main__':

    # loads path from config
    results_path = config['paths']['results']
    logic_rules_info_path = config['paths']['logic_rules_extraction_info']
    dt_info_path = config['paths']['ml_models_training_info']
    output_file = f"{results_path}/plots/times_table.png"

    rules_types = enumerate(config['rules_types'])

    algo_target_pairs = ['', 'anticipate_sol', 'anticipate_time', 'anticipate_memory',
                         'contingency_sol', 'contingency_time', 'contingency_memory']

    if not os.path.exists(logic_rules_info_path):
        raise FileExistsError(f"Result file not found: {logic_rules_info_path}")
    if not os.path.exists(dt_info_path):
        raise FileExistsError(f"Result file not found: {dt_info_path}")

    rows = []

    ### DECISION TREES RESULTS ###
    result_df = pd.read_csv(f"{dt_info_path}/dt_training_info.csv")
    training_times = result_df['training_time']
    riga_tt = [f"DT_training_time"] + [f"{x:.4f}" for x in training_times]
    rows.append(riga_tt)

    ### LOGIC RULES RESULTS ###
    for file in os.listdir(logic_rules_info_path):
        result_df = pd.read_csv(f"{logic_rules_info_path}/{file}")

        file_name = file.split('.')[0]
        rule = file_name.split('_')[-1]

        training_times = result_df['training_time']
        extraction_times = result_df['extraction_time']

        riga_tt = [f"{rule}_training_time"] + [f"{x:.4f}" for x in training_times]
        riga_et = [f"{rule}_extraction_time"] + [f"{x:.4f}" for x in extraction_times]

        rows.append(riga_tt)
        rows.append(riga_et)

        if rule == 'gridex' or rule == 'gridrex':
            pedro_times = result_df['pedro_time']
            riga_pt = [f"{rule}_pedro_time"] + [f"{x:.4f}" for x in pedro_times]
            rows.append(riga_pt)


df_finale = pd.DataFrame(rows, columns=algo_target_pairs)

### BUILD FINAL TABLE ###
fig, ax = plt.subplots(figsize=(13, len(df_finale) * 0.5 + 1))
ax.axis("off")

table = ax.table(
    cellText=df_finale.values,
    colLabels=df_finale.columns,
    loc="center",
    cellLoc="center"
)

table.auto_set_font_size(False)
table.set_fontsize(10)
table.scale(1.25, 1.5)

plt.plot()
plt.savefig(output_file)