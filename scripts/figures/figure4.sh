#!/usr/bin/bash

# Resolve repository root relative to this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"
export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"

# Config 1 -> paper Fig. 4, top-right panel  (N=2, J_2) -> Figures_paper/NE2_2_Percentage_0.4_J2.png
objective_params="{
    \"number of holes\": 2,
    \"radius\": 0.9, 
    \"top displacement\": 0.1,
    \"path\": \"$REPO_ROOT/data/initial_solutions/n2_2d\",
    \"path_solutions\": [\"solution-2.h5\", \"solution-0.h5\", \"solution-4.h5\"],
    \"i1\": [0, 2],
    \"i2\": [1, 1],
    \"percentage\": 0.4,
    \"coef_pen\": 0.001}"
step=1e-3
optimization_params="{
    \"initial_radius\": $step,
    \"max_radius\": 10*$step,
    \"radius_growing_rate\": 1.1,

    \"step_tol\": 1e-8,
    \"max_its\": 15,
    \"grad_tol\": 1e-8
}"
python3 -m src.experiment2 "$objective_params" "$optimization_params"
#############################################################################################

# Config 2 -> paper Fig. 4, top-left panel   (N=2, J_1) -> Figures_paper/NE2_2_Percentage_0.4_J1.png
objective_params="{
    \"number of holes\": 2,
    \"radius\": 0.9, 
    \"top displacement\": 0.1,
    \"path\": \"$REPO_ROOT/data/initial_solutions/n2_2d/\",
    \"path_solutions\": [\"solution-2.h5\", \"solution-0.h5\", \"solution-4.h5\"],
    \"i1\": [0],
    \"i2\": [1],
    \"percentage\": 0.4,
    \"coef_pen\": 0.001
}"
step=1e-3
optimization_params="{
    \"initial_radius\": $step,
    \"max_radius\": 10*$step,
    \"radius_growing_rate\": 1.1,

    \"step_tol\": 1e-8,
    \"max_its\": 20,
    \"grad_tol\": 1e-8,
}"
python3 -m src.experiment2 "$objective_params" "$optimization_params"
# ##############################################################################################

# Config 3 -> paper Fig. 4, bottom-right panel (N=4, J_2) -> Figures_paper/NE2_4_Percentage_0.4_J2.png
objective_params="{
    \"number of holes\": 4,
    \"radius\": 0.85, 
    \"top displacement\": 0.1,
    \"path\": \"$REPO_ROOT/data/initial_solutions/n4_2d\",
    \"path_solutions\": [\"solution-0.h5\", \"solution-35.h5\", \"solution-6.h5\"],
    \"i1\": [0, 2],
    \"i2\": [1, 1],
    \"percentage\": 0.4,
    \"coef_pen\": 0.001
    }"
step=1e-3
optimization_params="{
    \"initial_radius\": $step,
    \"max_radius\": 10*$step,
    \"radius_growing_rate\": 1.1,

    \"step_tol\": 1e-6,
    \"max_its\": 20,
    \"grad_tol\": 1e-8,
    }"
python3 -m src.experiment2 "$objective_params" "$optimization_params"
# ##############################################################################################

# Config 4 -> paper Fig. 4, bottom-left panel  (N=4, J_1) -> Figures_paper/NE2_4_Percentage_0.4_J1.png
objective_params="{
    \"number of holes\": 4,
    \"radius\": 0.85, 
    \"top displacement\": 0.1,
    \"path\": \"$REPO_ROOT/data/initial_solutions/n4_2d/\",
    \"path_solutions\": [\"solution-0.h5\", \"solution-35.h5\", \"solution-6.h5\"],
    \"i1\": [0],
    \"i2\": [1],
    \"percentage\": 0.4,
    \"coef_pen\": 0.001
}"
step=1e-3
optimization_params="{
    \"initial_radius\": $step,
    \"max_radius\": 10*$step,
    \"radius_growing_rate\": 1.1,

    \"step_tol\": 1e-8,
    \"max_its\": 20,
    \"grad_tol\": 1e-8,
}"
python3 -m src.experiment2 "$objective_params" "$optimization_params"
# #############################################################################################

