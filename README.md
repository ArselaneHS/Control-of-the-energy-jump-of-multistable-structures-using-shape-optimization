# Controlling the energy jump of multistable structures using shape optimization

**Authors:** Arselane Hadj Slimane, Patrick E. Farrell, Alberto Paganini, Àlex Ferrer

This repository provides reproducibility material for the paper "Controlling the energy jump of multistable structures using shape optimization."

## Overview

This repository implements a shape-optimization framework for controlling the energy jump between solution branches of hyperelastic metamaterials: we seek a domain deformation that tunes the snap-through energy gap between multiple solutions of a nonlinear elasticity problem.

The code is built around Firedrake, Fireshape, pyadjoint and ROL, and is organized so that experiments are driven from a small set of entry points in [src/](src).

## 1. Problem statement

We consider a hyperelastic body occupying a domain $\Omega$ and seek a shape deformation such that the energy jump between two selected stable branches, through an unstable branch, is moved toward a prescribed target ratio with respect to the original energy gap. In practice, this means:

- for the initial domain: solve a nonlinear elasticity problem on a domain with holes with deflated continuation;
- evaluate the energy gap between selected solutions;
- compute the shape gradient that acts as a deformation to update the domain;
- compute the solutions on the new domain from the old solutions (similar to a continuation with respect to the domain deformation);
- repeat optimization steps until convergence.

The mathematical formulation is described in the paper. The implementation follows the same workflow: initial solutions are loaded from checkpoint files, an objective functional is built from those solutions, and a shape optimization loop updates the domain.

The paper considers two objective functionals, and the distinction shows up directly in the run configurations below:

$$J_1(\Omega)=\left(\frac{\Delta\mathcal{E}_{1,2}(\Omega)}{\Delta\mathcal{E}_{1,2}(\Omega_0)}-r\right)^2,\qquad
J_2(\Omega)=\left(\frac{\Delta\mathcal{E}_{1,2}(\Omega)}{\Delta\mathcal{E}_{1,2}(\Omega_0)}-r\right)^2+\left(\frac{\Delta\mathcal{E}_{3,2}(\Omega)}{\Delta\mathcal{E}_{3,2}(\Omega_0)}-r\right)^2.$$

In the parameter dictionaries, $J_1$ corresponds to `"i1": [0], "i2": [1]` (one controlled gap) and $J_2$ to `"i1": [0, 2], "i2": [1, 1]` (two controlled gaps). The target ratio $r$ is the `percentage` entry.

## 2. Reproducibility and environment setup

The code depends on a specific Firedrake/Fireshape stack and cannot be installed from PyPI alone: Firedrake, PETSc, SLEPc and Netgen must already be present and consistent with one another, and ParaView is a system package. **Building and running the provided Docker image is the supported way to reproduce the results.**

### 2.1 What the environment must provide

| Component  | Version used for the paper                                                                    | Notes                                            |
| ---------- | --------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| Base image | `fireshape/fireshape@sha256:fd31374c80b3191074739bf4669c38221e0276c624dd6b375ea76faa3fcffd36` | Pinned by digest in the [Dockerfile](Dockerfile) |
| Firedrake  | `2025.10.2`                                                                                   | Checked out and reinstalled inside the image     |
| Fireshape  | as shipped in the base image                                                                  |
| defcon     | `master` from `bitbucket.org/pefarrell/defcon`                                                | Only needed to regenerate initial data           |
| ParaView   | `6.1.0` (MPI, Linux, Python 3.12)                                                             | Provides `pvpython`; **not** pip-installable     |
| Python     | `>= 3.12.3`                                                                                   | Matches the base image                           |

The remaining Python dependencies are declared in [pyproject.toml](pyproject.toml) and [requirements.txt](requirements.txt).

### 2.2 Build and run the Docker image (recommended)

The [Dockerfile](Dockerfile) pins the base image by digest, checks out the exact Firedrake tag, installs defcon and ParaView, copies the folder into `/opt/project`, and installs it in editable mode.


```bash
DOCKER_BUILDKIT=1 docker build \
  -t shape-opt-energy-jump:latest .

docker run -it --rm shape-opt-energy-jump:latest
```

Inside the container the project lives at `/opt/project`, which is also the working directory.

The build context is about 300 MB, almost all of it the checkpoints in
`data/initial_solutions`; [.dockerignore](.dockerignore) keeps `.git` and any
local `data/results` out.

### 2.3 Shell environment required by every entry point

All Python entry points are **modules under the `src` package** and use absolute `src.*` imports, so they must be launched from the repository root with that root on `PYTHONPATH`:

```bash
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"
export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"
```

Running `python src/experiment2.py ...` by file path is **not** supported: it does not put the repository root on `sys.path` and fails on `import src.*`.

Every script in [scripts/](scripts) performs this setup itself, resolving the repository root from its own location, so the scripts can be launched from anywhere.

If importing `netgen` fails, put the system site-packages ahead of the default search path:

```bash
export PYTHONPATH=/usr/local/lib/python3.12/site-packages:$PYTHONPATH
export PATH="/root/.local/bin:$PATH"
```

ParaView renders off-screen and therefore needs a virtual display. The figure scripts do this themselves; to run `pvpython` by hand:

```bash
rm -f /tmp/.X99-lock /tmp/.X11-unix/X99
Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp &
export DISPLAY=:99
```


### 2.4 Verifying the installation

The cheapest end-to-end check is a short 2-D run, which exercises mesh construction, checkpoint loading, the PDE solves, the ROL loop and the plotting path:

```bash
python3 -m src.experiment1
```

It prints the initial objective value and energy jumps, then the path of the results directory it created. A pure post-processing check that performs zero optimization steps (`max_its: 0`) and additionally exercises ParaView is `bash scripts/figures/figure1.sh`.

### 2.5 Expected outputs

Runs are deterministic given the same environment, the results directory name is a wall-clock timestamp (see [§3](#3-repository-structure-and-path-handling)).

Absolute objective values depend on the Firedrake/PETSc build; the quantities reported in the paper are ratios ($\Delta\mathcal{E}/\Delta\mathcal{E}^0$ against the target $r$), which are robust to that. 

## 3. Repository structure and path handling

```text
.
├── data/
│   ├── initial_solutions/      # checkpoint files used as starting points
│   │   ├── n2_2d/  n2_3d/      # 2 holes, radius 0.9
│   │   └── n4_2d/  n4_3d/      # 4 holes, radius 0.85
│   ├── paraview_saves/         # ParaView screenshots (created on demand)
│   └── results/                # one timestamped folder per run (created on demand)
├── scripts/
│   ├── figures/                # one script per paper figure  (see §5)
│   └── bash_submissions/       # the same runs grouped by experiment driver
├── src/
│   ├── base.py                 # BaseExperiment: the common workflow
│   ├── experiment1..4.py       # entry points
│   ├── Objective.py            # objective functional and factory
│   ├── Optimization.py         # ROL optimization loop
│   ├── initialisation_utils/   # mesh generation, deflated continuation, 3-D extrusion
│   └── utils/                  # paths, plotting, ROL output parsing, ParaView...
├── Dockerfile
├── pyproject.toml
└── README.md
```

All data and results paths are resolved relative to the repository root by [src/utils/paths.py](src/utils/paths.py), which exposes `repo_root()`, `data_dir()`, `results_base_dir()`, `resolve_path()`, `ensure_dir()`, `make_results_path_from_objective()` and `make_results_directory()`. A relative `"path"` entry in `objective_params` is resolved against the repository root, so runs never depend on the current working directory.

Within each `initial_solutions/` directory: `solution-<k>.h5` is a Firedrake checkpoint (mesh plus the CG2 displacement field `solution`) of defcon branch `k` at load $\lambda_0 = 0.1$; `eigenfunctions-<k>.h5` holds the eigenmodes from defcon's stability computation on that branch, and `functional-<k>.txt` the two defcon functionals (mean vertical displacement and a point value). Only the three `solution-*.h5` files listed in §6.4 are read by the experiments; the remaining files are provided as the full continuation output.

Each run creates a **flat, timestamped** directory:

```text
data/results/experiment_<YYYYmmdd_HHMMSS>/
```


## 4. Core code modules

### 4.1 Experiment drivers

The scripts directly under [src/](src) are the user-facing entry points. They differ only in how they loop over the `percentage` parameter:

- [src/base.py](src/base.py): `BaseExperiment`, the common workflow class — `prepare_results_dir()` → `build_objective()` → `run_optimization()` → `postprocess()`.
- [src/experiment1.py](src/experiment1.py): minimal single run with hard-coded parameters.
- [src/experiment2.py](src/experiment2.py): command-line driven single optimization at one target ratio.
- [src/experiment3.py](src/experiment3.py): independent runs across a list of target ratios, plus a combined cross-ratio figure.
- [src/experiment4.py](src/experiment4.py): continuation across a list of target ratios, reusing one objective instance (warm start).

### 4.2 Objective and optimization

- [src/Objective.py](src/Objective.py):
  - `EnergyJumpControl(PDEconstrainedObjective)` — solves the nonlinear elasticity problem for every branch and evaluates the gap-matching objective plus a `coef_pen`-weighted penalty that prevents branches from collapsing onto one another. Each Newton solve is seeded from the previous domain's solution, which is what keeps the branches identified across shape updates.
  - `make_objective()` — loads the checkpoints, builds the mesh and control space, and returns `(J, q, Q)`.
  - `save_objective_params()` / `make_results_directory()` — write the run record and create the output folder.
- [src/Optimization.py](src/Optimization.py): `ROL_optimization()` runs a ROL trust-region method (Dogleg subproblem, limited-memory BFGS secant) and records the trust-region flags.

### 4.3 Initialisation and data generation

- [src/initialisation_utils/get_initial_data.py](src/initialisation_utils/get_initial_data.py): builds the perforated Netgen/OCC geometry and returns the mesh together with the `top`/`bottom` boundary labels.
- [src/initialisation_utils/defcon_hyperelasticity.py](src/initialisation_utils/defcon_hyperelasticity.py): the deflated-continuation workflow that computes the initial solution branches. Use this to reproduce the initial data provided in the checkpoints in `data/initial_solutions`.
- [src/initialisation_utils/Hyperelasticity3d.py](src/initialisation_utils/Hyperelasticity3d.py): extends the 2-D solutions into 3-D initial guesses on an extruded mesh. Thus providing the initial solutions for the 3D runs, saved as checkpoints in `data/initial_solutions`.

### 4.4 Utilities

- [src/utils/paths.py](src/utils/paths.py): path resolution and results-folder creation.
- [src/utils/plotting.py](src/utils/plotting.py): objective, energy and energy-gap plots, and the CSV traces behind them.
- [src/utils/rol_output.py](src/utils/rol_output.py): captures ROL's stdout and extracts the trust-region flags used to filter rejected iterations out of the plots.
- [src/utils/paraview_save.py](src/utils/paraview_save.py), [src/utils/paraview_save_NE3.py](src/utils/paraview_save_NE3.py): ParaView screenshots of the initial and optimized domains.

## 5. Reproducing the figures in the paper

Each script in [scripts/figures](scripts/figures) is self-contained: it resolves the repository root, sets `PYTHONPATH`, runs every configuration needed for that figure, and — where the figure contains rendered geometries — starts `Xvfb` and calls ParaView.

```bash
bash scripts/figures/figure4.sh
```

| Paper figure                                                   | command                                                         | Driver                       | Results/figures path                                                        |
| -------------------------------------------------------------- | --------------------------------------------------------------- | ---------------------------- | --------------------------------------------------------------------------- |
| Fig. 1 — initial domain $\Omega_0$ and its three equilibria    | bash ./scripts/figures/[figure1.sh](scripts/figures/figure1.sh) | `experiment2` (`max_its: 0`) | `data/paraview_saves/experiment_<ts>/{Omega0,OmegaT}.png`                   |
| Fig. 2 — energy-landscape illustration                         | —                                                               | —                            | Hand-drawn illustration, not generated by this code                         | — |
| Fig. 3 — optimization iterates from initial to optimized shape | bash ./scripts/figures/[figure3.sh](scripts/figures/figure3.sh) | `experiment3`                | `data/paraview_saves/experiment_<ts>/progression_Omega.png`                 |
| Fig. 4 — convergence histories, single target ratio            | bash ./scripts/figures/[figure4.sh](scripts/figures/figure4.sh) | `experiment2`                | one `data/results/experiment_<ts>/` per run                                 |
| Fig. 5 — convergence histories across target ratios            | bash ./scripts/figures/[figure5.sh](scripts/figures/figure5.sh) | `experiment3`                | `data/results/experiment_<ts>/` (sweep root, with `percentage_<r>/` inside) |
| Fig. 6 — continuation in the target ratio                      | bash ./scripts/figures/[figure6.sh](scripts/figures/figure6.sh) | `experiment4`                | one `data/results/experiment_<ts>/` per continuation                        |
| Fig. 7 — geometries along the continuation                     | bash ./scripts/figures/[figure7.sh](scripts/figures/figure7.sh) | `experiment4`                | `data/paraview_saves/experiment_<ts>/{Omega0,OmegaT}.png`                   |
| Fig. 8 — 3-D geometries, $N=2$                                 | bash ./scripts/figures/[figure8.sh](scripts/figures/figure8.sh) | `experiment2`                | `data/paraview_saves/experiment_<ts>/{Omega0,OmegaT}.png`                   |
| Fig. 9 — 3-D geometries, $N=4$                                 | bash ./scripts/figures/[figure9.sh](scripts/figures/figure9.sh) | `experiment2`                | `data/paraview_saves/experiment_<ts>/{Omega0,OmegaT}.png`                   |

Notes on the table:

- All figure from 1 to 7 can be regenerated on a standard laptop machine under 10min. Figures 8 and 9 for the 3-D results take substantially more time. 
- Scripts that contain several configurations create **one timestamped results directory per configuration**, in the order the configurations appear in the script.
- The generated PNG file names are automatically derived from the run parameters (for example `NE2_2_Percentage_0.4.png`). 
- [scripts/bash_submissions](scripts/bash_submissions) contains the same runs grouped by experiment driver rather than by figure; the figure scripts are the entry point to prefer.
- To inspect the precise parameters and configurations used to produce a figure, refer to its corresponding file `./scripts/figures/figure*.sh`.

```bash
pvpython src/utils/paraview_save.py \
  --pvd_path data/results/experiment_<ts>/solution/u.pvd \
  --save_path data/paraview_saves/my_run \
  [--is_3d]
```

## 6. Running your own experiments

### 6.1 Minimal example

```bash
python3 -m src.experiment1
```

which uses:

```python
objective_params = {
    "number of holes": 2,
    "radius": 0.9,
    "top displacement": 0.1,
    "path": "./data/initial_solutions/n2_2d/",
    "path_solutions": ["solution-2.h5", "solution-0.h5", "solution-4.h5"],
    "i1": [0, 2],
    "i2": [1, 1],
    "percentage": 0.2,
    "coef_pen": 1e-3,
}

optimization_params = {
    "initial_radius": 0.005,
    "max_radius": 0.5,
    "radius_growing_rate": 1.5,
    "step_tol": 1e-6,
    "max_its": 20,
    "grad_tol": 1e-6,
}
```

### 6.2 Command-line runs

`experiment2`, `experiment3` and `experiment4` take two Python dictionary literals as arguments. They are passed through `eval()`, so Python expressions (`10*1e-3`) and trailing commas are valid:

```bash
python3 -m src.experiment2 \
  "{'number of holes': 2, 'radius': 0.9, 'top displacement': 0.1,
    'path': './data/initial_solutions/n2_2d/',
    'path_solutions': ['solution-2.h5', 'solution-0.h5', 'solution-4.h5'],
    'i1': [0, 2], 'i2': [1, 1], 'percentage': 0.2, 'coef_pen': 1e-3}" \
  "{'initial_radius': 0.005, 'max_radius': 0.5, 'radius_growing_rate': 1.5,
    'step_tol': 1e-6, 'max_its': 20, 'grad_tol': 1e-6}"
```

### 6.3 Parameter reference

`objective_params`:

| Key                | Meaning                                                                                                                               |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------- |
| `number of holes`  | Number of holes used to rebuild the boundary labels; the grid is $n\times(n+2)$ holes, the first and last column being half-holes on the vertical edges                                             |
| `radius`           | Relative hole radius (0 = points, 1 = holes in contact)                                                                               |
| `top displacement` | Imposed vertical displacement on the top boundary                                                                                     |
| `path`             | Directory holding the initial checkpoint files (relative paths resolve against the repository root)                                   |
| `path_solutions`   | Checkpoint files to load, in order; they become $u_1, u_2, \dots$                                                                     |
| `i1`, `i2`         | Equal-length index lists selecting which pairs of loaded solutions define the controlled energy gaps                                  |
| `percentage`       | Target ratio $r$ for the energy gap relative to its initial value. A scalar for `experiment2`; a list for `experiment3`/`experiment4` |
| `coef_pen`         | Weight of the penalty term that keeps the branches apart                                                                              |
| `height`           | **Optional.** Its presence switches the problem to 3-D on an extruded mesh                                                            |

`optimization_params`: `initial_radius`, `max_radius`, `radius_growing_rate`, `step_tol`, `grad_tol`, `max_its`. `experiment4` instead takes the lists `initial_radiuses` and `max_radiuses`, zipped against `percentage`.

Note that `number of holes` and `radius` do **not** define the mesh. They are used only to reconstruct the `top` and `bottom` boundary labels; the mesh itself is always loaded from the first checkpoint in `path_solutions`. They must nevertheless describe the same geometry as that checkpoint, or the labels will be wrong.

### 6.4 Regenerating the initial data

Initializing the objective requires several solutions on the initial configuration $\Omega_0$. These come from a deflated-continuation run in the load parameter, implemented in [src/initialisation_utils/defcon_hyperelasticity.py](src/initialisation_utils/defcon_hyperelasticity.py). This step is expensive and is normally performed once offline; the results are committed under [data/initial_solutions](data/initial_solutions) for the two configurations used in the paper — `number of holes = 2, radius = 0.9` (`n2_2d`) and `number of holes = 4, radius = 0.85` (`n4_2d`).

To re-generate the (2-D) initial data, run: 
```bash
python3 -m src.initialisation_utils.defcon_hyperelasticity -n 2 --r-coef 0.9
```
and 
```bash
python3 -m src.initialisation_utils.defcon_hyperelasticity -n 4 --r-coef 0.85
```

Running a deflated-continuation analysis takes a considerable time. The output files are named after defcon's branch index (`solution-<k>.h5`), and deflated continuation does not guarantee stable branch numbering across runs or library versions, so a regenerated data set will in general use different indices. The three branches used in the paper are therefore identified by their physical character rather than by index:

| role | physical branch | `n2_2d` (N=2) | `n4_2d` (N=4) |
| --- | --- | --- | --- |
| $u_2$ | mirror-symmetric (about $x=\tfrac12$) unbuckled configuration; the highest-energy branch, through which the snap-through passes | `solution-0.h5`, $\mathcal{E}=1465.35$ | `solution-35.h5`, $\mathcal{E}=1701.97$ |
| $u_1$ | one of the two mirror-image buckled configurations (lowest energy) | `solution-2.h5`, $\mathcal{E}=875.22$, $\bar u_x=+1.86\times10^{-2}$ | `solution-0.h5`, $\mathcal{E}=1299.01$, $M_1=-6.1\times10^{-4}$ |
| $u_3$ | the mirror image of $u_1$: $u_3(x,y)=(-u_{1,x},u_{1,y})(1-x,y)$ | `solution-4.h5`, $\mathcal{E}=876.51$, $\bar u_x=-1.86\times10^{-2}$ | `solution-6.h5`, $\mathcal{E}=1298.72$, $M_1=+5.6\times10^{-4}$ |

$\mathcal{E}=\int_\Omega \psi(u)-B\cdot u$ is the total potential energy at $\lambda_0=0.1$ (the quantity printed as the initial energies at start-up), $\bar u_x$ the mean horizontal displacement and $M_1=\int_\Omega u_x\,(y-\tfrac12)$  the first moment; the last two are handedness indicators that flip sign under $x\mapsto 1-x$ and vanish for a symmetric branch (for N=4 the buckled pattern has no net lateral shift, hence the moment). To re-identify branches in a  regenerated set, take the mirror-symmetric branch of highest energy as $u_2$ and the two lowest-energy branches, which are mirror images of each other, as $u_1$ and $u_3$;

```bash
python3 -m src.utils.identify_branches data/initial_solutions/n2_2d
```

prints these quantities for every checkpoint in a directory. Since $u_1$ and $u_3$ are related by reflection, swapping them reproduces the optimized shapes up to the same reflection. The 3-D checkpoints (`n2_3d`, `n4_3d`) keep the index of the 2-D file they were lifted from.


The 3-D initial data (`n2_3d`, `n4_3d`) is produced from the 2-D checkpoints by [src/initialisation_utils/Hyperelasticity3d.py](src/initialisation_utils/Hyperelasticity3d.py), which solves on an extruded mesh using the 2-D solutions as initial guesses. To re-generate the 3-D initial data (from the 2-D solutions), run:
```bash
python3 -m src.initialisation_utils.Hyperelasticity3d -n 2 --r-coef 0.9
```
and 
```bash
python3 -m src.initialisation_utils.Hyperelasticity3d -n 4 --r-coef 0.85
```


## 7. Outputs

Each run directory `data/results/experiment_<ts>/` contains:

```text
objective_params.txt          # objective parameters, as used
optimization_parameters.txt   # ROL parameters, as used
solution/u.pvd                # domain and solutions at every accepted iterate (+ u/*.vtu)
results_data/*.csv            # objective, per-branch energies and energy gaps vs iteration
<name>.png                    # convergence figure for the run
```

The CSV traces are two-column (`x,y`) files: `objs.csv`, and one `energies_<label>.csv` per branch. The energy-gap traces are named after the plot that produced them: the default `all_deltas` plot (experiments 1-3) writes one file per *pair* of branches, named after the gap itself (e.g. `$\Delta\mathcal{E}(u_1,u_2)$.csv`), while the `deltas` plot (experiment 4) writes `delta_<i1>_<i2>.csv` per controlled gap. Iterations rejected by the trust region are filtered out of both the plots and the CSVs, using the flags parsed from ROL's output.

## 8. License

This code is released under the BSD 3-Clause License; see [LICENSE](LICENSE).

Note that the runtime dependencies carry their own, separate terms — Firedrake
and PETSc are LGPL, and ParaView is BSD-3-Clause. The Docker image built from
[Dockerfile](Dockerfile) bundles them and is therefore governed by those terms
as well as this one.
