#!/usr/bin/bash

# Resolve repository root relative to this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"
export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"

#############################################################################################
# Config 1 -> paper Fig. 3, SECOND row (J_2). The four panels of the generated
# progression_Omega.png are Omega_0 and the optimized shapes for r = 0.6, 0.4, 0.2;
# they were split out as Figures_paper/{Omega0,Omega_D2_T1,Omega_D2_T2,Omega_D2_T3}.png
objective_params="{
    \"number of holes\": 2,
    \"radius\": 0.9, 
    \"top displacement\": 0.1,
    \"path\": \"$REPO_ROOT/data/initial_solutions/n2_2d/\",
    \"path_solutions\": [\"solution-2.h5\", \"solution-0.h5\", \"solution-4.h5\"],
    \"i1\": [0, 2],
    \"i2\": [1, 1],
    \"percentage\": [0.6, 0.4, 0.2],
    \"coef_pen\": 0.0001
}"
step=1e-3
optimization_params="{
    \"initial_radius\": $step,
    \"max_radius\": 10*$step,
    \"radius_growing_rate\": 1.2,

    \"step_tol\": 1e-6,
    \"max_its\": 15,
    \"grad_tol\": 1e-4,
}"
TS1="$(date +%Y%m%d_%H%M%S)"
RESULTS_DIR_1="$REPO_ROOT/data/results/experiment_$TS1"
SAVE_DIR_1="$REPO_ROOT/data/paraview_saves/experiment_$TS1"
python3 -m src.experiment3 "$objective_params" "$optimization_params" "$RESULTS_DIR_1"

rm -f /tmp/.X99-lock /tmp/.X11-unix/X99
Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp &
XVFB_PID=$!
export DISPLAY=:99
pvpython "$REPO_ROOT/src/utils/paraview_save_NE3.py" \
  --exp_dir "$RESULTS_DIR_1" \
  --save_path "$SAVE_DIR_1" \
  --percentages=[0.6,0.4,0.2]
kill $XVFB_PID 2>/dev/null || true
############################################################################################

# Config 2 -> paper Fig. 3, FIRST row (J_1); split as Figures_paper/Omega_D1_T{1,2,3}.png
objective_params="{
    \"number of holes\": 2,
    \"radius\": 0.9, 
    \"top displacement\": 0.1,
    \"path\": \"$REPO_ROOT/data/initial_solutions/n2_2d/\",
    \"path_solutions\": [\"solution-2.h5\", \"solution-0.h5\", \"solution-4.h5\"],
    \"i1\": [0],
    \"i2\": [1],
    \"percentage\": [0.6, 0.4, 0.2],
    \"coef_pen\": 0.001
}"
step=1e-2/2
optimization_params="{
    \"initial_radius\": $step,
    \"max_radius\": 10*$step,
    \"radius_growing_rate\": 1.1,

    \"step_tol\": 1e-5,
    \"max_its\": 25,
    \"grad_tol\": 1e-4,
}"
TS2="$(date +%Y%m%d_%H%M%S)"
RESULTS_DIR_2="$REPO_ROOT/data/results/experiment_$TS2"
SAVE_DIR_2="$REPO_ROOT/data/paraview_saves/experiment_$TS2"
python3 -m src.experiment3 "$objective_params" "$optimization_params" "$RESULTS_DIR_2"


rm -f /tmp/.X99-lock /tmp/.X11-unix/X99
Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp &
XVFB_PID=$!
export DISPLAY=:99
pvpython "$REPO_ROOT/src/utils/paraview_save_NE3.py" \
  --exp_dir "$RESULTS_DIR_2" \
  --save_path "$SAVE_DIR_2" \
  --percentages=[0.6,0.4,0.2]
kill $XVFB_PID 2>/dev/null || true
# # ##############################################################################################
