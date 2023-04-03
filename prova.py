
for algorithm in ["anticipate", "contingency"]:
    for target in ["memory", "time"]:
        for re in ["GridRex", "GridEx", "CART", "CReEPy"]:
            f = open("algorithms/rules/"+algorithm+"_pc_"+target+"_"+re+".txt", "x")
            f.write("")
            f.close()
