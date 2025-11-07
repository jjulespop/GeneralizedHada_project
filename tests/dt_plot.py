'''Plots bar diagrams for solving results'''

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from hada.config import config_loader

config = config_loader.load_config(config_path="./hada/config/config.yaml")



if __name__ == '__main__':

    # loads path from config
    results_path = config['paths']['results']
    result_folder = f"{results_path}/computations"
    plots_folder = f"{results_path}/plots"

    for file in os.listdir(result_folder):
        df = pd.read_csv(f"{result_folder}/{file}", index_col=0)

        file_name = file.split('.')[0]
        y_label = file_name.split('_')[1]

        match y_label:
            case 'time':
                yl = 'ex_times(s)'
            case 'vars':
                yl = 'n_vars'
            case 'constraints':
                yl = 'n_constraints'

        # get rows and columns
        models = df.index
        targets = df.columns.astype(str)
        x = np.arange(len(targets))
        bar_width = 0.15

        plt.figure(figsize=(8, 5))

        # draw bars
        for i, model in enumerate(models):
            plt.bar(x + (i - len(models)/2) * bar_width + bar_width/2,
                    df.loc[model],
                    width=bar_width,
                    label=model
                )

            # add bars labels
            for j, val in enumerate(df.loc[model]):
                label = f"{int(val)}" if float(val).is_integer() else f"{val:.3f}"
                plt.text(x[j] + (i - len(models)/2) * bar_width + bar_width/2,
                        val + 0.01,
                        label,
                        ha='center', 
                        fontsize=8
                    )
                
        target_labels = [1, 2, 3]

        # add legend and axis names
        plt.xlabel('targets', fontsize=12, fontweight='bold')
        plt.ylabel(yl, fontsize=12, fontweight='bold')
        plt.xticks(x, target_labels)
        plt.legend()
        plt.tight_layout()
        plt.plot()

        # save plot
        plt.savefig(f"{plots_folder}/{file_name}_plot.png")

