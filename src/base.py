"""
Base experiment runner for Shape-Optimization-of-Energy-Jump.

Provides a `BaseExperiment` class that encapsulates common workflow steps:
 - load/validate parameters
 - initialize mesh and solutions
 - build objective functional
 - run optimization
 - post-process and plotting

Each concrete experiment script should create or receive `objective_params`
and `optimization_params` and call `BaseExperiment.run(...)`.
"""
from typing import Optional, Dict, Any
import os
import shutil
import logging
import matplotlib.pyplot as plt
import numpy as np

from src.Objective import make_objective, make_results_directory
from src.Optimization import ROL_optimization
from src.utils.plotting import plot_results, plot_NE3
from pathlib import Path

logger = logging.getLogger("experiments.base")
logging.basicConfig(level=logging.INFO)


class BaseExperiment:
    def __init__(self, objective_params: Dict[str, Any], optimization_params: Optional[Dict[str, Any]] = None, NE: int = 2):
        self.objective_params = objective_params
        self.optimization_params = optimization_params or {}
        self.NE = NE
        self.results_path = None
        self.J = None
        self.q = None
        self.Q = None
        self.results = None

    def prepare_results_dir(self, clean: bool = True, parent_dir: Optional[str] = None) -> str:
        """Create a results directory for this experiment and return its path."""
        path = os.fspath(parent_dir) if parent_dir is not None else make_results_directory(self.objective_params, NE=self.NE)
        if clean:
            shutil.rmtree(path, ignore_errors=True)
            os.makedirs(path, exist_ok=True)
        self.results_path = path
        logger.info(f"Results path: {self.results_path}")
        return self.results_path

    def build_objective(self, write: bool = True, **kwargs):
        """Construct the objective functional using project's factory function.

        After this call, `self.J`, `self.q`, `self.Q` are set.
        """
        if self.results_path is None:
            self.prepare_results_dir()
        self.J, self.q, self.Q = make_objective(self.objective_params, results_path=self.results_path, write=write, **kwargs)
        logger.info("Objective created")
        return self.J, self.q, self.Q

    def run_optimization(self):
        """Run the optimization routine (ROL wrapper) with the provided params."""
        if self.J is None or self.q is None:
            self.build_objective()
        logger.info("Starting optimization")
        ROL_optimization(self.J, self.q, self.optimization_params, results_path=self.results_path)
        logger.info("Optimization finished")

    def postprocess(self, plots=None, post_process=True, name_plot: Optional[str] = None):
        """Run plotting/post-processing steps and return collected results."""
        self.results = self.J.eval_cb_post(self.J, self.J)
        self.J.rol_tr_flags = [flag for flag in self.J.rol_tr_flags if flag != 5]
        self.J.rol_tr_flags+=[self.J.rol_tr_flags[-1]] 
        if plots is None:
            plots = ["energies", "all_deltas", "objs"]
        plot_results(self.J, self.results, self.results_path, plots=plots, post_process=True, name_plot=name_plot)
        logger.info("Postprocessing done")
        return self.results
    
    def plot_NE3(self, list_objs, list_deltas, list_tr_flags, percentages,  name_plot: Optional[str] = None):
        """Plot results for NE=3 experiments across percentages."""
        if self.J is None:
            raise RuntimeError("Objective not built. Call build_objective() first.")
        plot_NE3(list_objs, list_deltas, list_tr_flags, percentages, self.objective_params, str(Path(self.results_path).parent), self.J, name_plot=name_plot)
        logger.info("NE=3 plotting done")

    def run(self, clean_results: bool = True, plots=None, post_process=True, name_plot: Optional[str] = None):
        self.prepare_results_dir(clean=clean_results)
        self.build_objective()
        self.run_optimization()
        results = self.postprocess(plots=plots, post_process=post_process, name_plot=name_plot)
        return results
