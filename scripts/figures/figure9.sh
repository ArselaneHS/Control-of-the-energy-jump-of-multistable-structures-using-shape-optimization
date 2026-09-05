#!/usr/bin/bash

# Resolve repository root relative to this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"
export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"


python3 -m src.utils.fspatch1
trap 'python3 -m src.utils.fspatch2 || true' EXIT
# Paper Fig. 9 (N=4, 3-D, J_2, r=0.2) -> Figures_paper/4_Holes3DSolution.png
objective_params="{
    \"number of holes\": 4,
    \"radius\": 0.85, 
    \"top displacement\": 0.1,
    \"path\": \"$REPO_ROOT/data/initial_solutions/n4_3d/\",
    \"path_solutions\": [\"solution-0.h5\", \"solution-35.h5\", \"solution-6.h5\"],
    \"i1\": [0, 2],
    \"i2\": [1, 1],
    \"percentage\": 0.2,
    \"coef_pen\": 0.001,
    \"height\": 1.0
}"
step=1e-3
optimization_params="{
    \"initial_radius\": $step,
    \"max_radius\": 500*$step,
    \"radius_growing_rate\": 1.2,

    \"step_tol\": 1e-6,
    \"max_its\": 20,
    \"grad_tol\": 1e-4,
}"
python3 -m src.experiment2 "$objective_params" "$optimization_params"

rm -f /tmp/.X99-lock /tmp/.X11-unix/X99
Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp &
XVFB_PID=$!
export DISPLAY=:99
pvpython  $REPO_ROOT/src/utils/paraview_save.py --is_3d True
kill $XVFB_PID 2>/dev/null || true
############################################################################################

