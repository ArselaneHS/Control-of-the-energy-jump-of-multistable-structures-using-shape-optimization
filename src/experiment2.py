"""Experiment 2 - command-line driven single optimization.

Usage:
    python -m src.experiment2 "{objective_params_dict}" "{optimization_params_dict}"

This script expects two eval-able dict strings on the command line (keeps compatibility
with existing workflows). It uses `BaseExperiment` to manage the run.
"""

import sys
from src.base import BaseExperiment


def main():
    if len(sys.argv) < 3:
        raise RuntimeError("Usage: experiment2 <objective_params> <optimization_params>")

    objective_params = eval(sys.argv[1])
    optimization_params = eval(sys.argv[2])

    runner = BaseExperiment(objective_params, optimization_params, NE=2)
    runner.prepare_results_dir(clean=True)
    runner.build_objective()
    runner.run_optimization()
    results = runner.postprocess(name_plot=f"NE2_{objective_params.get('number of holes','')}_Percentage_{objective_params.get('percentage','')}.png")
    print("Experiment 2 finished. Results saved to:", runner.results_path)


if __name__ == "__main__":
    main()

