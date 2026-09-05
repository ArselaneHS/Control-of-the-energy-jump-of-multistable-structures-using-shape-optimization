from firedrake import *
from fireshape import *
import fireshape.zoo as fsz
import ROL
import pandas as pd
from pathlib import Path
import os

from pyadjoint.adjfloat import AdjFloat
from pathlib import Path

import logging
import shutil
import matplotlib.pyplot as plt
import itertools
import numpy as np
from matplotlib.ticker import MaxNLocator

logging.getLogger("matplotlib").setLevel(logging.WARNING)
logging.getLogger("matplotlib.mathtext").setLevel(logging.WARNING)

from src.Objective import EnergyJumpControl
from src.initialisation_utils.get_initial_data import *


plt.rcParams.update({
    'font.size': 22,         # Default text size
    'axes.titlesize': 25,    # Axes title size
    'axes.labelsize': 25,    # Axes label size
    'xtick.labelsize': 25,   # X tick label size
    'ytick.labelsize': 25,   # Y tick label size
    'legend.fontsize': 27,   # Legend font size
    'lines.linewidth': 4,    # Line plot thickness
})


FIGURE_WIDTH_PER_PANEL = 10
FIGURE_HEIGHT = 10
def make_consistent_figure(n_panels):
    """Create a figure with a fixed physical size per subplot."""
    fig_width = max(1, n_panels) * FIGURE_WIDTH_PER_PANEL
    fig, ax = plt.subplots(
        1,
        n_panels,
        figsize=(fig_width, FIGURE_HEIGHT),
        constrained_layout=True,
    )
    if n_panels == 1:
        ax = [ax]
    return fig, ax


def post_process_results(J,results):
    # Post-process results using ROL trust region flags to filter out iterations where the trust region was not accepted.
    rol_tr_flags = [flag for flag in J.rol_tr_flags if flag !=5]
    bools = (np.array(rol_tr_flags)==0)

    results["objs"] = np.array(results["objs"])[bools]

    for key in results["energies"].keys():
        results["energies"][key] = np.array(results["energies"][key])[bools]
    for key in results["deltas"].keys():
        results["deltas"][key] = np.array(results["deltas"][key])[bools]
    return results


def plot_results(J,results,results_path, plots, post_process=False, p=0, name_plot=None):
    """Plot the results.
    
    Parameters
    ----------
    J : EnergyJumpControl class - Objective functional.
    results : dict
        Results from the optimization.
        deltas : list - List of energy jumps.
        energies : list - List of energy values.
        objs : list - List of objective values.
    results_path : str - Path to save the plots.
    """
    # Post-process results
    if post_process:
        results = post_process_results(J,results)

    
    deltas = results["deltas"]
    energies = results["energies"]
    objs = results["objs"]

    # Convert results to numpy arrays
    for key in energies.keys():
        energies[key] = np.array(energies[key])
    for key in deltas.keys():
        deltas[key] = np.array(deltas[key])
    objs = np.array(objs)
    n_its = len(objs)


    # Create results directory
    p= J.objective_params["percentage"]
    if results_path is None:
        from src.utils.paths import make_results_directory
        results_path = make_results_directory(J.objective_params)


    # Make plots
    n=len(plots)
    fig, ax = make_consistent_figure(n)
    os.makedirs(Path(results_path)/Path('results_data/'), exist_ok=True)
    import matplotlib.ticker as mticker

    linestyles = ['-', '--', ':', '-.']
    markers = ['o', 's', '^', 'd', 'x', '*']
    marker_stride = 1
    marker_size = 12
    line_width = 3.0
    print(plots)
    for id_plot,plot in enumerate(plots):
        if plot == "objs":
            ax[id_plot].plot(
                objs,
                label=fr'$J(\Omega)$',
                marker='o',
                markersize=marker_size,
                markevery=marker_stride,
                linewidth=line_width,
            )
            ax[id_plot].set_xlabel('iteration')
            ax[id_plot].set_ylabel(r'Objective')
            ax[id_plot].legend()
            ax[id_plot].xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
            np.savetxt(Path(results_path)/'results_data/objs.csv', np.column_stack((np.arange(len(objs)), objs)), delimiter=',', header="x,y", comments="")

        elif plot == "energies":
            for idx, key in enumerate(energies.keys()):
                current_linestyle = linestyles[idx % len(linestyles)]
                current_marker = markers[idx % len(markers)]
                ax[id_plot].plot(
                    energies[key],
                    label=key,
                    linestyle=current_linestyle,
                    marker=current_marker,
                    markersize=marker_size,
                    markevery=marker_stride,
                    linewidth=line_width,
                )
                np.savetxt(Path(results_path)/f'results_data/energies_{key}.csv', np.column_stack((np.arange(len(energies[key])), energies[key])), delimiter=',', header="x,y", comments="", fmt=['%d', '%.6f'])

            ax[id_plot].set_xlabel('iteration')
            ax[id_plot].set_ylabel(fr'Energy $\mathcal{{E}}(u)$')
            ax[id_plot].legend()
            ax[id_plot].xaxis.set_major_locator(mticker.MaxNLocator(integer=True))

        elif plot == "deltas":
            for idx, (i,j) in enumerate(zip(J.objective_params["i1"],J.objective_params["i2"])):
                current_linestyle = linestyles[idx % len(linestyles)]
                current_marker = markers[idx % len(markers)]
                key=fr"$\Delta\mathcal{{E}}({J.u[min(i,j)].name()},{J.u[max(i,j)].name()})$"
                D=deltas[key]
                ax[id_plot].plot(
                    D/D[0],
                    label=key+fr"$/\Delta\mathcal{{E}}^0$",
                    linestyle=current_linestyle,
                    marker=current_marker,
                    markersize=marker_size,
                    markevery=marker_stride,
                    linewidth=line_width,
                )
                np.savetxt(Path(results_path)/f'results_data/delta_{i}_{j}.csv', np.column_stack((np.arange(len(D)), D)), delimiter=',', header="x,y", comments="", fmt=['%d', '%.6f'])
            for pp in p:
                ax[id_plot].axhline(y=pp, linestyle='dashed', color='gray')
            ax[id_plot].set_xlabel('iteration')
            ax[id_plot].set_ylabel(fr"$\Delta\mathcal{{E}}/\Delta\mathcal{{E}}^0$")
            ax[id_plot].legend()
            ax[id_plot].xaxis.set_major_locator(mticker.MaxNLocator(integer=True))

        elif plot=="all_deltas":
            ii,jj=J.objective_params["i1"][0],J.objective_params["i2"][0]
            # Common normalizer for every pair, so that uncontrolled gaps stay on the
            # same scale as the controlled one. min/max: deltas is keyed ascending.
            delta0= abs(deltas[fr"$\Delta\mathcal{{E}}({J.u[min(ii,jj)].name()},{J.u[max(ii,jj)].name()})$"][0])
            for idx, key in enumerate(deltas.keys()):
                current_linestyle = linestyles[idx % len(linestyles)]
                current_marker = markers[idx % len(markers)]
                D=deltas[key]
                ax[id_plot].plot(
                    np.abs(D)/delta0,
                    label=key+r'$/\Delta\mathcal{E}^0$',
                    linestyle=current_linestyle,
                    marker=current_marker,
                    markersize=marker_size,
                    markevery=marker_stride,
                    linewidth=line_width,
                )
                ax[id_plot].axhline(y=p, linestyle='dashed', color='gray')
                np.savetxt(Path(results_path)/fr'results_data/{key}.csv', np.column_stack((np.arange(len(D)), D)), delimiter=',', header="x,y", comments="", fmt=['%d', '%.6f'])
            ax[id_plot].set_xlabel('iteration')
            ax[id_plot].set_ylabel(fr'Energy gap $\Delta\mathcal{{E}}/\Delta\mathcal{{E}}^0$')
            ax[id_plot].legend()
            ax[id_plot].xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
        else:
            raise ValueError(f"Unknown plot: {plot}")
        
    if name_plot is None:
        name_plot = f"Percentage {p}.png"

    save_path = Path(results_path) / name_plot
    plt.savefig(save_path)
    plt.close()


def plot_NE3( list_objs, list_deltas, list_tr_flags, percentages, objective_params, results_path, J,  name_plot = None):
    """Plot results for NE=3 experiments across percentages."""
    i1 = objective_params["i1"]
    objective_params = objective_params
    n_deltas=len(i1)

    linestyles = ['-', '--', ':', '-.']
    markers = ['o', 's', '^', 'd', 'x', '*']
    line_width = 4.0
    marker_size = 12
    marker_stride = 1

    fig, ax = make_consistent_figure(n_deltas+1)
    for p_idx, p in enumerate(percentages):

        current_linestyle = linestyles[p_idx % len(linestyles)]
        current_marker = markers[p_idx % len(markers)]

        objs = list_objs[p_idx]
        objs = np.array(objs)

        temp = list_tr_flags[p_idx]
        rol_tr_flags = [flag for flag in temp if flag !=5]
        bools = (np.array(rol_tr_flags)==0)

        ax[0].xaxis.set_major_locator(MaxNLocator(integer=True))
        ax[0].plot(objs / objs[0], label=f'ratio {p}', linestyle=current_linestyle, marker=current_marker, markersize=marker_size, linewidth=line_width, markevery=marker_stride)
        ax[0].set_xlabel('Iteration')
        ax[0].set_ylabel(fr'Objective $J(\Omega)$')
        ax[0].legend()

        deltas = list_deltas[p_idx]
        ii, jj = objective_params["i1"][0], objective_params["i2"][0]
        key = fr"$\Delta\mathcal{{E}}({J.u[min(ii,jj)].name()},{J.u[max(ii,jj)].name()})$"
        delta0=deltas[key][0]

        for it in range(1, n_deltas+1 ):
            ax[it].xaxis.set_major_locator(MaxNLocator(integer=True))
            ii, jj = objective_params["i1"][it-1], objective_params["i2"][it-1]
            key = fr"$\Delta\mathcal{{E}}({J.u[min(ii,jj)].name()},{J.u[max(ii,jj)].name()})$"
            D=deltas[key]
            ax[it].plot(D/D[0], label=fr'ratio {p}', linestyle=current_linestyle, marker=current_marker, markersize=marker_size, linewidth=line_width, markevery=marker_stride)
            ax[it].axhline(y=p, linestyle='dashed', color='gray')
            ax[it].set_xlabel('Iteration')
            ax[it].set_ylabel(fr'$\Delta\mathcal{{E}}($'+fr"${J.u[objective_params['i1'][it-1]].name()}$"+','+fr"${J.u[objective_params['i2'][it-1]].name()}$"+r'$)/\Delta\mathcal{E}^0$')
            ax[it].legend()

    plt.tight_layout()
    filename = name_plot if name_plot else f"ROL_NE3_{objective_params['number of holes']}_holes_delta{len(objective_params['i1'])}.png"
    plt.savefig(os.path.join(results_path, filename))
    plt.close()


def generate_readme(path_solutions, N_holes, lmbda0, results_path,p,i1,i2):
    """Generate a README file with the given parameters."""

    readme_content = f"""
    # Shape Optimization of Energy Jump

    ## Parameters

    - **Number of Holes**: {N_holes}
    - **Displacement**: {lmbda0}

    ## Objective 
    - **Solutions**:{path_solutions}
    """
    objective=f""" """
    for i in range(len(i1)):
        delta=f"""- $\\Delta_{i}(\\Omega)= |\\psi({path_solutions[i1[i]]}) - \\psi({path_solutions[i2[i]]})|$ """
        readme_content+=delta
        objective+=f"""$(\\Delta_{i}(\\Omega)-{p}*\\Delta_{i}(\\Omega_0))^2$""" 
    readme_content +="""
    - **Objective**:"""+ objective


    readme_content +="""

    ## Results
    The results of the optimization are saved in the specified results path and include plots of deltas, energies, and norms.
    """
    with open(results_path+"/README.md", "w") as readme_file:
        readme_file.write(readme_content)

