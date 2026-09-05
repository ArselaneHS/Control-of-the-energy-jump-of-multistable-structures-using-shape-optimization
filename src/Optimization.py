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


def optimization_loop(J, q, dq, optimization_params, write=True,p=0, pvd_file=None, results_path=None):
    """Perform the optimization loop
    
    Parameters
    ----------
    J : EnergyJumpControl
        Objective functional.
    q : ControlVector
    step : float - Initial step size.
    alpha : float - Step size reduction factor.
    beta : float - Step size increase factor.
    step_tol : float - Step tolerance.
    max_its : int - Maximum number of iterations.
    pvd_file : VTKFile - VTK file to write the solution.
    write : bool - Whether to write the solution to a VTK file.

    Returns
    -------
    deltas : list - List of energy jumps.
    energies : list - List of energy values.
    objs : list - List of objective values.
    norms : list - List of norms between solutions.
    norms2 : list - List of norms between solution at step t and t-1.
    """

    #callback function
    p_temp= J.p_float if p==0 else p
    if write:
        if results_path is None:
            # Construct a canonical results path using objective parameters
            results_path = str(make_results_path_from_objective(J.objective_params, NE=0))
        if pvd_file is None:
            pvd_file=VTKFile(results_path+"/solution/u.pvd")
    else:
        pvd_file=None

    save_optimization_parameters(results_path, False, **optimization_params)

    t = 0
    Jold = J.value(None, None)
    deltas, energies ,objs,norms, norms2 = [],[],[],[],[]


    print(f"i={t} | J={J.value(None, None):e}| ", flush=True)
    callback(J,pvd_file)
    save_results(J,deltas, energies ,objs,Jold,norms,norms2)

    dq_temp=q.clone()
    J.value(None, None)
    J.gradient(dq_temp, None, None)

    step=optimization_params["step"]/dq_temp.norm()
    alpha=optimization_params["step-size reduction factor"]
    beta=optimization_params["step-size increase factor"]
    max_decrease=optimization_params["max_decrease"]

    step_tol=optimization_params["step_tol"]/dq_temp.norm()
    max_its=optimization_params["max_its"]
    obj_tol=optimization_params["obj_tol"]

    while True:

        J.gradient(dq, None, None)
        while True:
            if step < step_tol:
                break
            q.axpy(-step, (dq))
            J.update(q, None, t)

            Jnew = J.objective_value()
            if Jnew > Jold or Jnew<max_decrease*Jold or Jnew == AdjFloat(np.nan) or np.isnan(Jnew):
                q.axpy(+step, dq)
                J.update(q, None, t)
                step *= alpha
                if Jnew == AdjFloat(np.nan) or np.isnan(Jnew):
                    print_nan(J,step*dq.norm(),Jnew,t)
                elif Jnew > Jold:
                    print(f" objective didn't decrease  | i={t} | step={step*dq.norm():e} | Jnew={Jnew:e}", flush=True)
                else:
                    print(f" branch switching  | i={t} | step={step*dq.norm():e} | Jnew={Jnew:e}", flush=True)
            else:
                step *= beta
                J_temp=Jold
                Jold = Jnew
                t += 1

                print(f"i={t} | J={J.value(None, None):e}| grad={dq.norm():e}", flush=True)
                callback(J,pvd_file)
                save_results(J,deltas, energies ,objs,Jold,norms,norms2)

                break

        if t > max_its - 1 or step < step_tol or abs(Jnew - J_temp) < obj_tol:
            if step < step_tol:
                print(f"--- step tol reached ---  i={t} | step={step*dq.norm():e}", flush=True)
            elif t > max_its - 1:
                print(f"--- max its reached ---  i={t} | step={step*dq.norm():e}", flush=True)
            elif abs(Jnew - Jold) < obj_tol:
                print(f"--- obj tol reached ---  i={t} | step={step*dq.norm():e}", flush=True)
            break

    results={
        "deltas": deltas,
        "energies": energies,
        "objs": objs,
        "norms": norms,
        "successive norms": norms2
    }
    return results

def callback(J, pvd_file):
    """Callback function to write VTK files."""
    if pvd_file is not None:
        pvd_file.write(*(J.u))

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


def save_results(J,deltas,energies,objs,obj,norms,norms2=None):
    """Save the results in the lists."""
    N_solutions=J.objective_params["number of solutions"]
    deltas.append([[float(abs(assemble((J.psi(J.u[i])-J.psi(J.u[j]))*dx))) for j in range(i+1,N_solutions)] for i in range(N_solutions-1)  ])
    energies.append([assemble(J.psi(u) * dx) for u in J.u])
    objs.append(obj)
    norms.append([[norm(J.u[i]-J.u[j]) for j in range(i+1,N_solutions)] for i in range(N_solutions-1)  ])

    norms2.append([norm(J.u[i]-J.up[i]) for i in range(N_solutions)])

def print_nan(J,step,Jnew,t):
    """ prints in case of NaN value """
    if J.tangled_mesh==True:
        print(f" tangled mesh  | i={t} | step={step:e} | Jnew={Jnew:e}", flush=True)
    elif J.failed_to_solve_elas==True:
        print(f" failed to solve elas  | i={t} | step={step:e} | Jnew={Jnew:e}", flush=True)
    elif J.collapse==True:
        print(f" collapse solutions  | i={t} | step={step:e} | Jnew={Jnew:e}", flush=True)
    else:
        print(f" NaN value  | i={t} | step={step:e} | Jnew={Jnew:e}", flush=True)

