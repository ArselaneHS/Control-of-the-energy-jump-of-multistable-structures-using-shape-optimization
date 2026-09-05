from firedrake import *
from fireshape import *

import sys

from src.initialisation_utils.get_initial_data import initialize_mesh
from src.base import BaseExperiment



if __name__ == "__main__":


    objective_params=eval(sys.argv[1])
    #### Initializing mesh
    N_holes=objective_params["number of holes"]
    r_coef= objective_params["radius"]
    lmbda0=0.1

    mesh, bottom, top = initialize_mesh(N_holes=N_holes, r_coef=r_coef, height=None)
    objective_params["bottom"]=bottom
    objective_params["top"]=top



    ### Objective functional
    Q = FeControlSpace(mesh)    
    q = ControlVector(Q, H1InnerProduct(Q, fixed_bids=top+bottom))

    percentages =  eval(sys.argv[2])  
    objective_params["percentage"] = percentages[0]  # Start with the first percentage

    i1, i2 = objective_params["i1"], objective_params["i2"]
    """Experiment 5 - independent per-delta continuation using BaseExperiment."""

    def main():
        if len(sys.argv) < 4:
            raise RuntimeError("Usage: experiment5 <objective_params> <percentages_list> <steps_list>")

        objective_params = eval(sys.argv[1])
        percentages = eval(sys.argv[2])
        steps = eval(sys.argv[3])

        # Start from first percentage and iterate through provided lists
        for p, step in zip(percentages, steps):
            print(f"Running percentage {p}")
            objective_params_local = dict(objective_params)
            objective_params_local["percentage"] = p
            optimization_params = {
                "initial_radius": step,
                "max_radius": 100 * step,
                "radius_growing_rate": 1.2,
                "step_tol": 1e-8,
                "max_its": 100,
                "grad_tol": 1e-8,
            }

            runner = BaseExperiment(objective_params_local, optimization_params, NE=5)
            runner.run(clean_results=False, name_plot=f"NE5_percentage_{p}.png")

        print("Experiment 5 finished.")


    if __name__ == "__main__":
        main()