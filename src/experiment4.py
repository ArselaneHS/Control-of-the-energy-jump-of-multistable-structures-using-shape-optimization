"""Experiment 4 - continuation over percentages using BaseExperiment."""

import sys
from src.base import BaseExperiment


def main():
    if len(sys.argv) < 3:
        raise RuntimeError("Usage: experiment4 <objective_params> <optimization_params>")

    objective_params = eval(sys.argv[1])
    optimization_params = eval(sys.argv[2])

    percentages = objective_params.get("percentage", [])
    if not isinstance(percentages, (list, tuple)):
        percentages = [percentages]

    # Prepare top-level results directory
    base_runner = BaseExperiment(objective_params, optimization_params, NE=4)
    results_path = base_runner.prepare_results_dir(clean=True)

    # single objective instance reused across percentages (warm-start behavior)
    base_runner.build_objective()
    tr_flags = []
    for p, step, max_radius in zip(percentages, optimization_params.get("initial_radiuses", []), optimization_params.get("max_radiuses", [])):
        print(f"Running percentage {p}")
        base_runner.J.p.assign(p)
        optimization_params_local = dict(optimization_params)
        optimization_params_local["initial_radius"] = step
        optimization_params_local["max_radius"] = max_radius
        base_runner.optimization_params = optimization_params_local
        base_runner.run_optimization()
        tr_flags = tr_flags+(base_runner.J.rol_tr_flags)
    base_runner.J.rol_tr_flags = tr_flags


    # # Postprocess once at the end
    results = base_runner.postprocess(plots=["deltas"],name_plot=f"ROL_NE4_{objective_params.get('number of holes','')}.png", post_process=True)
    print("Experiment 4 finished. Results saved to:", base_runner.results_path)


if __name__ == "__main__":
    main()