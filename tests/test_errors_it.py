import pandas


from core.configdb import ConfigDB
from core.logic_models import LogicModels


#bounds = {"time": [60, 120, 180, 300, None], 'memory': [100, 200, 300, 350, None], 'sol': [300, 340, 380, 420, None]}
#bounds = {"sol": [250, 314,   340,  363, 393, None], 'memory': [59, 87, 88, 141, 241,  None], 'time': [1,  22, 41, 59, 151,  None]}
bounds= {"sol": [250, 313, 339, 362, 392, None], 'memory': [59, 86, 87, 140, 241, None], 'time': [1, 21, 40, 58, 150, None]}
#bounds = {"time": [None], 'memory': [None], 'sol': [None]}
targets = ["sol", "time", "memory"]
rules_type = "CART"
db = ConfigDB.from_local('./algorithms/configs')
lr = LogicModels(db, "algorithms/logic_rules", rules_type)


stats = {}
counter = {}
similar = 0
different = 0
for algorithm in ['anticipate', 'contingency']:
    stats[algorithm] = {"ex_times": 0, "n_vars": 0, "n_constraints": 0, "ex_memory_mean": 0, "ex_memory_max": 0}
    counter[algorithm] = 0
    rules = {}
    for target in targets:
        rules[target] = lr.get_rules(algorithm, "pc", target)
    for objective in targets:
        new_bounds = bounds.copy()
        new_bounds.pop(objective)
        bound_targets = list(new_bounds.keys())
        current_bounds = {objective: "obj"}
        current_bounds_n = {objective: "obj"}
        for i in range(len(new_bounds[bound_targets[0]])):
            first_bound = current_bounds[bound_targets[0]] = new_bounds[bound_targets[0]][i]
            for j in range(len(new_bounds[bound_targets[1]])):
                """if first_bound is not None:
                    current_bounds[bound_targets[1]] = None
                else:
                    if second_bound is None:
                        continue
                    current_bounds[bound_targets[1]] = second_bound"""
                second_bound = current_bounds[bound_targets[1]] = new_bounds[bound_targets[1]][j]
                mem_bound = current_bounds["memory"]
                sol_bound = current_bounds["sol"]
                time_bound = current_bounds["time"]
                file_name = f'results_it_f/cart/results_{algorithm}_{objective}_m{mem_bound}_t{time_bound}_s{sol_bound}.csv'
                df = pandas.read_csv(file_name)
                sol_hp = df["sol_hyperparam"]
                sol_time = df["sol_time"]
                sol_memory = df["sol_memory"]
                sol_sol = df["sol_sol"]
                input = df[["load_mean", "load_std", "sol_hyperparam", "pv_mean", "pv_std"]]
                if algorithm == "anticipate":
                    input = input.rename(columns={"sol_hyperparam": "nScenarios"})
                if algorithm == "contingency":
                    input = input.rename(columns= {"sol_hyperparam": "nTraces"})
                #print(input.head())
                pred_sol = lr.predict(rules["sol"], input)
                pred_time = lr.predict(rules["time"], input)
                pred_memory = lr.predict(rules["memory"], input)
                for i in range (30):
                    diff_sol = float(pred_sol[i]) - float(sol_sol[i])
                    diff_time = float(pred_time[i]) - float(sol_time[i])
                    diff_memory = float(pred_memory[i]) - float(sol_memory[i])
                    if abs(diff_sol) >= 0.1 or abs(diff_memory) >= 0.1 or abs(diff_time) >= 0.1:
                        print("different")
                        print(f'{algorithm} {objective} {i} {first_bound} {second_bound}')
                        different += 1
                        print(f'{sol_sol[i]} {pred_sol[i]}')
                        print(diff_sol)
                        print(f'{sol_time[i]} {pred_time[i]}')
                        print(diff_time)
                        print(f'{sol_memory[i]} {pred_memory[i]}')
                        print(diff_memory)
                        print("---------------------------------------------------------")
                    else:
                        similar += 1
                        #print("similar")
                        #print("---------------------------------------------------------")

                """if first_bound is not None:
                    break"""

print(f'similar {similar}')
print(f'different {different}')