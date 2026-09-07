#!/usr/bin/bash

# Resolve repository root relative to this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"
export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"

# Paper Fig. 1 (N=2, Omega_0 and its three equilibria) -> Figures_paper/figure1_Omega0.png
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
step=0.0
optimization_params="{
    \"initial_radius\": $step,
    \"max_radius\": 10*$step,
    \"radius_growing_rate\": 1.0,

    \"step_tol\": 1e-8,
    \"max_its\": 0,
    \"grad_tol\": 1e-8
}"
TS="$(date +%Y%m%d_%H%M%S)"
RESULTS_DIR="$REPO_ROOT/data/results/experiment_$TS"
SAVE_DIR="$REPO_ROOT/data/paraview_saves/experiment_$TS"
python3 -m src.experiment2 "$objective_params" "$optimization_params" "$RESULTS_DIR"

rm -f /tmp/.X99-lock /tmp/.X11-unix/X99
Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp &
XVFB_PID=$!
export DISPLAY=:99
pvpython "$REPO_ROOT/src/utils/paraview_save.py" \
  --pvd_path "$RESULTS_DIR/solution/u.pvd" \
  --save_path "$SAVE_DIR"
kill $XVFB_PID 2>/dev/null || true


