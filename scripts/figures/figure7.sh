#!/usr/bin/bash

# Resolve repository root relative to this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"
export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"

# Config 1 -> paper Fig. 7, rows 1-2: Omega_0 and the shape after minimizing J_2 at r=1.6
#             -> Figures_paper/figure7_Omega0.png, figure7_OmegaT_1.png
objective_params="{
    \"number of holes\": 4,
    \"radius\": 0.85, 
    \"top displacement\": 0.1,
    \"path\": \"$REPO_ROOT/data/initial_solutions/n4_2d\",
    \"path_solutions\": [\"solution-0.h5\",\"solution-35.h5\",\"solution-6.h5\"],
    \"i1\": [0, 2],
    \"i2\": [1, 1],
    \"coef_pen\": 0.00001,
    \"percentage\": [1.1, 1.2, 1.3, 1.6]
}"
optimization_params="{
    \"initial_radiuses\": [1e-2/2, 1e-2, 1e-2, 1e-2 ],
    \"max_radiuses\": [1e-2/2, 1e-2, 1e-2, 1e-2 ],
    \"radius_growing_rate\": 1.3,

    \"step_tol\": 1e-8,
    \"max_its\": 15,
    \"grad_tol\": 1e-8,
}"
TS1="$(date +%Y%m%d_%H%M%S)"
RESULTS_DIR_1="$REPO_ROOT/data/results/experiment_$TS1"
SAVE_DIR_1="$REPO_ROOT/data/paraview_saves/experiment_$TS1"
python3 -m src.experiment4 "$objective_params" "$optimization_params" "$RESULTS_DIR_1"

rm -f /tmp/.X99-lock /tmp/.X11-unix/X99
Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp &
XVFB_PID=$!
export DISPLAY=:99
pvpython "$REPO_ROOT/src/utils/paraview_save.py" \
  --pvd_path "$RESULTS_DIR_1/solution/u.pvd" \
  --save_path "$SAVE_DIR_1"
kill $XVFB_PID 2>/dev/null || true
# ##############################################################################################


# Config 2 -> paper Fig. 7, row 3: the shape after minimizing J_1 at r=0.2
#             -> Figures_paper/figure7_OmegaT_2.png
objective_params="{
    \"number of holes\": 4,
    \"radius\": 0.85, 
    \"top displacement\": 0.1,
    \"path\": \"$REPO_ROOT/data/initial_solutions/n4_2d\",
    \"path_solutions\": [\"solution-0.h5\", \"solution-35.h5\", \"solution-6.h5\"],
    \"i1\": [0],
    \"i2\": [1],
    \"percentage\": [0.6, 0.4, 0.2],
    \"coef_pen\": 0.001,
}"
optimization_params="{
    \"initial_radiuses\": [1e-3,1e-3,0.005],
    \"max_radiuses\": [1e-3,1e-3,0.005],
    \"radius_growing_rate\": 1.2,

    \"step_tol\": 1e-6,
    \"max_its\": 15,
    \"grad_tol\": 1e-4,
}"
TS2="$(date +%Y%m%d_%H%M%S)"
RESULTS_DIR_2="$REPO_ROOT/data/results/experiment_$TS2"
SAVE_DIR_2="$REPO_ROOT/data/paraview_saves/experiment_$TS2"
python3 -m src.experiment4 "$objective_params" "$optimization_params" "$RESULTS_DIR_2"

rm -f /tmp/.X99-lock /tmp/.X11-unix/X99
Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp &
XVFB_PID=$!
export DISPLAY=:99
pvpython "$REPO_ROOT/src/utils/paraview_save.py" \
  --pvd_path "$RESULTS_DIR_2/solution/u.pvd" \
  --save_path "$SAVE_DIR_2"
kill $XVFB_PID 2>/dev/null || true
# ############################################################################################


