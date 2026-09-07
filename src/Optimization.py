from firedrake import *
from fireshape import *
import fireshape.zoo as fsz
import ROL
import pandas as pd

from pyadjoint.adjfloat import AdjFloat

import logging
import shutil
import matplotlib.pyplot as plt
import numpy as np

logging.getLogger("matplotlib").setLevel(logging.WARNING)
logging.getLogger("matplotlib.mathtext").setLevel(logging.WARNING)

from src.Objective import EnergyJumpControl
from src.initialisation_utils.get_initial_data import *
from src.utils.rol_output import capture_stream_output, extract_rol_tr_flags
from pathlib import Path
from src.utils.paths import make_results_path_from_objective, ensure_dir


def ROL_optimization(J,q, optimization_params, results_path=None, p=None):
    """Perform the optimization using ROL.
    
    Parameters
    ----------
    J : EnergyJumpControl
        Objective functional.
    q : ControlVector
    step_tol : float - Step tolerance.
    max_its : int - Maximum number of iterations.

    Remark
    -------
    The results are saved by J in the lists J.deltas, J.energies, J.objs, J.norms, and J.norms2
    J.deltas: list - List of energy jumps.
    J.energies: list - List of energy values.
    J.objs: list - List of objective values.
    J.norms: list - List of norms between solutions.
    """

    # Set the results path
    p_temp= J.p_float if p==None else p
    if results_path is None:
        results_path = str(make_results_path_from_objective(J.objective_params, NE=0))

    # Save optimization parameters
    save_optimization_parameters(results_path, True, **optimization_params)



    # Trust Region parameters
    params_dict = {
    'Step':{'Type':'Trust Region',
            'Trust Region':{'Initial Radius':optimization_params["initial_radius"], #determine initial radius with heuristics
                            'Maximum Radius':optimization_params["max_radius"], #determine maximum radius with heuristics
                            'Subproblem Solver':'Dogleg',
                            'Radius Growing Rate': optimization_params["radius_growing_rate"],
                            'Step Acceptance Threshold':0.05,
                            'Radius Shrinking Threshold':0.05,
                            'Radius Growing Threshold':0.9,
                            'Radius Shrinking Rate (Negative rho)':0.0625,
                            'Radius Shrinking Rate (Positive rho)':0.25,
                            'Sufficient Decrease Parameter':1.e-4,
                            'Safeguard Size':100.0,
                        }
        },
    'General':{'Print Verbosity':0, #set to any number >0 for increased verbosity
            'Secant':{'Type':'Limited-Memory BFGS', #BFGS-based Hessian-update in trust-region model
                        'Maximum Storage':10
                        }
            },
    'Status Test': {'Gradient Tolerance': optimization_params["grad_tol"],
                    'Step Tolerance': optimization_params["step_tol"],
                    'Iteration Limit': optimization_params["max_its"]}
    }

    # Set up ROL optimizer
    params = ROL.ParameterList(params_dict, "Parameters")
    problem = ROL.OptimizationProblem(J, q)
    solver = ROL.OptimizationSolver(problem, params)

    # Run ROL optimization and capture the output
    rol_output = capture_stream_output(solver.solve)
    print(rol_output, end="", flush=True)

    # Extract ROL trust region flags from the ROL output and store them in J.rol_tr_flags
    J.rol_tr_flags = [0] + extract_rol_tr_flags(rol_output)
    return J.rol_tr_flags



def save_optimization_parameters(results_path, ROL, **params):
    """Save optimization parameters to a file.

    Parameters
    ----------
    results_path : str
        Path to save the parameters file.
    **params : dict
        Dictionary of parameters to save.
    """
    p = Path(results_path)
    ensure_dir(p)
    params_file = p / "optimization_parameters.txt"
    with params_file.open("w") as file:
        file.write("Optimization Parameters:\n")
        file.write(f"ROL: {ROL}\n")
        for key, value in params.items():
            file.write(f"{key}: {value}\n")



