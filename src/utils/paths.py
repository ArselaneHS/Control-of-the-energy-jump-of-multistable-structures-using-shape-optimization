"""Repository path utilities using pathlib.

Provide a single source of truth for data and results folder locations.
"""
from datetime import datetime
from pathlib import Path
from typing import Union

import sys
import glob
import os
import re

import os
import re
import numpy as np


def repo_root() -> Path:
    """Return the repository root (two levels above this file: src/ -> repo)."""
    return Path(__file__).resolve().parents[2]


def data_dir() -> Path:
    return repo_root() / "data"


def initial_solutions_dir() -> Path:
    return data_dir() / "initial_solutions"


def paraview_saves_dir() -> Path:
    return data_dir() / "paraview_saves"


def results_base_dir() -> Path:
    return data_dir() / "results"


def results_experiments_dir(dim: int = 2, NE: int = 0) -> Path:
    """Return the base results directory for experiments of given dimension and experiment number.

    Example: results_experiments_dir(dim=2, NE=3) -> <repo>/data/results/experiments_2d/experiments3
    """
    dim_suffix = f"experiments_{dim}d"
    return results_base_dir() / dim_suffix / f"experiments{NE}"


def ensure_dir(p: Union[str, Path]):
    Path(p).mkdir(parents=True, exist_ok=True)


def make_results_path_from_objective(objective_params: dict, NE: int = 0) -> Path:
    """Return a timestamped experiment results directory under data/results.

    The project used to create deeply nested objective-specific paths. New runs
    should create a single folder named ``experiment_<timestamp>`` under the
    top-level results directory. The objective params and experiment number are
    kept only for compatibility with old callers and are ignored in the path.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return results_base_dir() / f"experiment_{timestamp}"


def make_results_directory(objective_params: dict, NE: int = 0) -> str:
    """Create and return the timestamped results directory for a run."""
    path = make_results_path_from_objective(objective_params, NE=NE)
    ensure_dir(path)
    return str(path)


def resolve_path(p: Union[str, Path]) -> Path:
    """Resolve a possibly-relative path against the repository root.

    If `p` is absolute, returns as Path; otherwise returns repo_root() / p.
    """
    p = Path(p)
    if p.is_absolute():
        return p
    return repo_root() / p


def find_matching_subfolder(base_path, target_value, tol=1e-12):
    """
    Find a subfolder in base_path with top boundary displacement 
    approximately equal to target_value.

    Parameters
    ----------
    base_path : str
        Path to the folder with output from defcon.
    target_value : float
        Target value of the top boundary displacement.
    tol : float
        Tolerance for numerical comparison.

    Returns
    -------
    str
        Path to the first matching subfolder.

    Raises
    ------
    FileNotFoundError
        If no matching folder is found.
    """
    for folder in os.listdir(base_path):
        full_path = os.path.join(base_path, folder)
        if os.path.isdir(full_path):
            # Try to extract the float value from folder name
            match = re.search(r"eps=([0-9eE\+\-\.]+)", folder)
            if match:
                try:
                    folder_eps = float(match.group(1))
                    if np.isclose(folder_eps, target_value, atol=tol):
                        return full_path
                except ValueError:
                    continue  # Skip if conversion fails

    raise FileNotFoundError(f"No matching folder found for eps ≈ {target_value}")


def get_solutions_paths(directory, pattern=r"solution-\d+\.h5"):
    """
    Isolates in directory the paths to the solutions.

    Parameters
    ----------
    directory : str - Path to the directory containing the solutions.
    pattern : str - Pattern of the file names of the solutions paths.

    Returns
    -------
    list - List of solutions paths.
    """

    regex = re.compile(pattern)
    res=[]
    for root, dirs, files in os.walk(directory):
        files.sort()
        for file in files:
            if regex.match(file):
                res.append(file)
    return res


def psi(u, dim=2):
    """ Needed for get_optimum_solutions_paths bellow"""
    # Imported here, not at module scope: this module is also imported by the
    # ParaView helpers, which run under pvpython and have no firedrake.
    from firedrake import Identity, grad, tr, det, Constant, ln

    # Kinematics
    I = Identity(dim)             # Identity tensor
    F = I + grad(u)             # Deformation gradient
    C = F.T*F                   # Right Cauchy-Green tensor

    # Invariants of deformation tensors
    Ic = tr(C)
    J  = det(F)

    # Elasticity parameters
    E, nu = 1000000.0, 0.3
    mu, lmbda_cte = Constant(E/(2*(1 + nu))), Constant(E*nu/((1 + nu)*(1 - 2*nu)))

    # Stored strain energy density (compressible neo-Hookean model)
    psi = (mu/2)*(Ic - dim) - mu*ln(J) + (lmbda_cte/2)*(ln(J))**2

    return psi

def get_optimum_solutions_paths(mesh,directory,solutions_paths=None, pattern=r"solution-\d+\.h5"):
    """Get the optimal solutions paths.

    Parameters
    ----------
    mesh : Mesh 
    directory : str - Path to the directory containing the solutions.
    solutions_paths : list - List of solutions paths.
    pattern : str - Pattern to match the solutions paths.

    Returns
    -------
    str - Name (file name in directory) of the solution with the minimum energy.
    str - Name (file name in directory) of the solution with the maximum energy.
    int - Index of the solution with the minimum energy.
    int - Index of the solution with the maximum energy.
    """

    from firedrake import VectorFunctionSpace, Function, CheckpointFile, assemble, project, dx

    if solutions_paths is None:
        solutions_paths = get_solutions_paths(directory, pattern)

    V=VectorFunctionSpace(mesh, "CG", 2)
    u = [Function(V,name=solutions_paths[i]) for i in range(len(solutions_paths))]
    energies = []
    for i in range(len(solutions_paths)):
        file=directory+solutions_paths[i]
        with CheckpointFile(file, 'r') as afile:
            meshh = afile.load_mesh('firedrake_default')
            temp = afile.load_function(meshh, 'solution')
            if temp.function_space().mesh() != u[i].function_space().mesh():
                temp = project(temp, u[i].function_space())
            u[i].assign(temp)
            energies.append(float(assemble(psi(u[i]) * dx)))

    i_min = np.argmin(energies)
    i_max = np.argmax(energies)

    print(f"u_min: {u[i_min].name()} | energy: {energies[i_min]}")
    print(f"u_max: {u[i_max].name()} | energy: {energies[i_max]}")

    return u[i_min].name(), u[i_max].name(),i_min,i_max

