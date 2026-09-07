"""Experiment 3 - parameter sweep across percentages using BaseExperiment."""

import sys
import os
from src.base import BaseExperiment
from src.utils.plotting import make_consistent_figure


def main():
    if len(sys.argv) < 3:
        raise RuntimeError("Usage: experiment3 <objective_params> <optimization_params>")

    objective_params = eval(sys.argv[1])
    optimization_params = eval(sys.argv[2])
    results_dir = sys.argv[3] if len(sys.argv) > 3 else None
    
    percentages = objective_params.get("percentage", [])
    if not isinstance(percentages, (list, tuple)):
        percentages = [percentages]

    results_base = BaseExperiment(objective_params, optimization_params, NE=3)
    sweep_results_path = results_base.prepare_results_dir(clean=True, parent_dir=results_dir)

    # create a figure space if desired (keeps previous plotting behavior)
    fig, ax = make_consistent_figure(1 + len(objective_params.get("i1", [])))

    list_objs = []
    list_deltas = []
    list_tr_flags = []
    for p in percentages:
        print(f"Running percentage {p}")
        objective_params_local = dict(objective_params)
        objective_params_local["percentage"] = p
        runner = BaseExperiment(objective_params_local, optimization_params, NE=3)
        percentage_results_path = os.path.join(sweep_results_path, f"percentage_{p}")
        runner.prepare_results_dir(clean=True, parent_dir=percentage_results_path)
        runner.build_objective()
        runner.run_optimization()
        results = runner.postprocess(name_plot=f"ROL_NE3_{objective_params.get('number of holes','')}_Percentage_{p}.png")


        # Collect results for plotting across percentages
        objs = results["objs"]
        deltas = results["deltas"]
        tr_flags = runner.J.rol_tr_flags
        list_objs.append(objs)
        list_deltas.append(deltas)
        list_tr_flags.append(tr_flags)
    # Plot results across percentages
    runner.plot_NE3(list_objs, list_deltas, list_tr_flags, percentages=percentages, name_plot=f"ROL_NE3_{objective_params.get('number of holes','')}_percentages_{objective_params.get('percentage','')}.png")
    print("Experiment 3 finished. Results saved to:", sweep_results_path)


if __name__ == "__main__":
    main()