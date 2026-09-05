from firedrake import *
from fireshape import *

"""Experiment 1 - simple single-run example using BaseExperiment."""
from src.base import BaseExperiment


def main():
    # Minimal hard-coded parameters (keeps original experiment behaviour)
    objective_params = {
        "number of holes": 2,
        "radius": 0.9,
        "top displacement": 0.1,
        "path": "./data/initial_solutions/n2_2d/",
        "path_solutions": ['solution-2.h5', 'solution-0.h5', 'solution-4.h5'],
        "i1": [0, 2],
        "i2": [1, 1],
        "percentage": 0.2,
        "coef_pen" : 1e-3,
    }

    optimization_params = {
        "initial_radius": 0.005,
        "max_radius": 0.5,
        "radius_growing_rate": 1.5,
        "step_tol": 1e-6,
        "max_its": 20,
        "grad_tol": 1e-6,
    }

    runner = BaseExperiment(objective_params, optimization_params, NE=2)
    results = runner.run(clean_results=True, name_plot="NE2_experiment1")
    print("Experiment 1 finished. Results saved to:", runner.results_path)


if __name__ == "__main__":
    main()
