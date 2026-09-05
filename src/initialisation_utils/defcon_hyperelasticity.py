# -*- coding: utf-8 -*-
from firedrake import *
from defcon import *
from netgen.occ import *
from firedrake.cython import dmcommon

import defcon.backend as backend
from slepc4py import SLEPc
from petsc4py import PETSc

import sys
import os
import re
import numpy as np
from datetime import datetime
from pathlib import Path
import argparse

from defcon import estimate_error_dwr
def custom_estimate_error_dwr(*args, **kwargs):
    pass
estimate_error_dwr = custom_estimate_error_dwr

# Path to the directory containing this script
SCRIPT_DIR = Path(__file__).resolve().parent

# REPO_ROOT = SCRIPT_DIR / "../.." resolved to an absolute path
REPO_ROOT = (SCRIPT_DIR / "../..").resolve()

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

class HyperelasticityProblem(BifurcationProblem):

    def __init__(self, n, r_coef=None ,*args, **kwargs):
        super().__init__( *args, **kwargs)
        self.n = n+1
        if r_coef is None:
            self.r_coef = 0.9
        else:
            self.r_coef = r_coef

    def mesh(self,comm):
        rect = WorkPlane(Axes((0,0,0), n=Z, h=X)).Rectangle(1,1).Face().bc("sides")
        rect.edges.Min(Y).name = "bottom"
        rect.edges.Max(Y).name = "top"

        shape = rect
        for i in range(1,self.n):
            for j in range(1, self.n+2):
                centre_x = (1/self.n)*(j-1)
                centre_y = (1/self.n)*(i+0)
                disk = WorkPlane(Axes((centre_x, centre_y, 0), n=Z, h=X)).Circle(self.r_coef*(1/(2*self.n))).Face()
                shape = shape - disk

        geo = OCCGeometry(shape, dim=2)
        ngmesh = geo.GenerateMesh(maxh=1)
        mesh = Mesh(ngmesh,comm=  comm)
        mh = MeshHierarchy(mesh, 2, netgen_flags={})
        mesh = mh[-1]

        self.bottom = [i + 1 for (i, name) in
                enumerate(ngmesh.GetRegionNames(codim=1)) if name == "bottom"]
        self.top    = [i + 1 for (i, name) in
                enumerate(ngmesh.GetRegionNames(codim=1)) if name == "top"]
        self.comm = comm

        return mesh


    def function_space(self, mesh):
        V = VectorFunctionSpace(mesh, "CG", 1)

        # Construct rigid body modes used in algebraic multigrid preconditioner later on
        x = SpatialCoordinate(mesh)
        rbms = [Constant((0, 1)),
                Constant((1, 0)),
                as_vector([-x[1], x[0]])]
        self.rbms = [Function(V).interpolate(rbm) for rbm in rbms]

        return V

    def parameters(self):
        eps = Constant(0)

        return [(eps, "eps", r"$\epsilon$")]

    def residual(self, u, params, v):
        eps=params[0]
        B   = Constant((0.0, -1000)) # Body force per unit volume

        # Kinematics
        I = Identity(2)             # Identity tensor
        F = I + grad(u)             # Deformation gradient
        C = F.T*F                   # Right Cauchy-Green tensor

        # Invariants of deformation tensors
        Ic = tr(C)
        J  = det(F)

        # Elasticity parameters
        E, nu = 1000000.0, 0.3
        mu, lmbda = Constant(E/(2*(1 + nu))), Constant(E*nu/((1 + nu)*(1 - 2*nu)))

        # Stored strain energy density (compressible neo-Hookean model)
        psi = (mu/2)*(Ic - 2) - mu*ln(J) + (lmbda/2)*(ln(J))**2

        # Total potential energy
        Energy = psi - dot(B, u) #- dot(T, u)*ds

        F=derivative(Energy*dx, u, v)
        return F

    def boundary_conditions(self, V, params):
        eps = params[0]
        bcl = DirichletBC(V, Constant((0.0,  0.0)), self.bottom)
        bcr = DirichletBC(V, Constant((0.0, -eps)), self.top)
        return [bcl,bcr]

    def functionals(self):
        def total_vertical_displacement(u, params):
            return assemble(u[1]*dx) / 0.1

        def pointeval(u, params):
            return u((0.25, 0.05))[1]

        return [(total_vertical_displacement, "total_vertical_displacement", r"$\frac{1}{|\Omega|} \int_\Omega u_1 \ \mathrm{d}x$", lambda u, params: Constant(10) * u[1]*dx),
                (pointeval, "pointeval", r"$u_1(0.25, 0.05)$")]

    def number_initial_guesses(self, params):
        return 1

    def initial_guess(self, V, params, n):
        return Function(V)

    def number_solutions(self, params):
        # Here I know the number of solutions for each value of eps.
        # This cheating allows me to calculate the bifurcation diagram
        # much more quickly. This can be disabled without changing the
        # correctness of the calculations.
        # eps = params[0]
        # if eps < 0.03:
        #     return 1
        # if eps < 0.07:
        #     return 3
        # if eps < 0.12:
        #     return 5
        # if eps < 0.18:
        #     return 7
        # if eps < 0.20:
        #     return 9
        return float("inf")

    def squared_norm(self, a, b, params):
        return inner(a - b, a - b)*dx + inner(grad(a - b), grad(a - b))*dx

    def solver(self, problem, params, solver_params, prefix="", **kwargs):
        firedrake_solver_args = ['nullspace', 'transpose_nullspace', 'appctx', 'pre_jacobian_callback', 'post_jacobian_callback', 'pre_function_callback', 'post_function_callback']
        valid_kwargs = {key: value for (key, value) in kwargs.items() if key in firedrake_solver_args}
        valid_kwargs["pre_apply_bcs"] = False # impose BCs like FEniCS
        return NonlinearVariationalSolver(
                problem, options_prefix=prefix,
                solver_parameters=solver_params,
                **valid_kwargs
            )


    # def solver(self, problem, params, solver_params, prefix="", **kwargs):
    #     # Set the rigid body modes for use in AMG

    #     s = BifurcationProblem.solver(self, problem, params, solver_params, prefix=prefix, pre_apply_bcs=False, **kwargs)
    #     snes = s.snes

    #     if snes.ksp.type != "preonly":
    #         # Convert rigid body modes (computed in self.function_space above) to PETSc Vec
    #         with self.rbms[0].dat.vec_ro as rbm_0, self.rbms[1].dat.vec_ro as rbm_1, self.rbms[2].dat.vec_ro as rbm_2:
    #             rbms = [rbm_0, rbm_1, rbm_2]

    #             # Create the PETSc nullspace
    #             nullsp = PETSc.NullSpace().create(vectors=rbms, constant=False, comm=snes.comm)

    #             (A, P) = snes.ksp.getOperators()
    #             A.setNearNullSpace(nullsp)
    #             P.setNearNullSpace(nullsp)

    #     return s

    def solver_parameters(self, params, task, **kwargs):
        return {
               "snes_max_it": 50,
               "snes_atol": 1.0e-7,
               "snes_rtol": 1.0e-10,
               "snes_max_linear_solve_fail": 100,
               "snes_linesearch_type": "l2",
               "snes_linesearch_maxstep": 1.0,
               "mat_type": "aij",
               "ksp_type": "gmres",
               "ksp_max_it": 2000,
               "pc_type": "lu", # switch to "gamg" for an inexact solver
               "pc_factor_mat_solver_type": "mumps",
               "eps_type": "krylovschur",
               "eps_target": -1,
               "eps_nev": 1,
               "st_type": "sinvert",
               "st_ksp_type": "preonly",
               "st_pc_type": "lu",
               "st_pc_factor_mat_solver_type": "mumps",
               }


    def compute_stability(self, params, branchid, u, hint=None):
        V = u.function_space()
        trial = TrialFunction(V)
        test = TestFunction(V)

        bcs = self.boundary_conditions(V, params)
        comm = V.mesh().comm

        F = self.residual(u, list(map(Constant, params)), test)
        J = derivative(F, u, trial)

        A = assemble(J, bcs=bcs)
        M = assemble(inner(test,trial)*dx, bcs=bcs)

        # There must be a better way of doing this
        from firedrake.preconditioners.patch import bcdofs
        lgmap = V.dof_dset.lgmap
        for bc in bcs:
            # Ensure symmetry of M
            M.M.handle.zeroRowsColumns(lgmap.apply(bcdofs(bc)), diag=0)

        # Create the SLEPc eigensolver
        eps = SLEPc.EPS().create(comm=comm)
        eps.setOperators(A.M.handle, M.M.handle)
        eps.setWhichEigenpairs(eps.Which.SMALLEST_MAGNITUDE)
        eps.setProblemType(eps.ProblemType.GHEP)
        eps.setFromOptions()

        # If we have a hint, use it - eigenfunctions from previous solve
        if hint is not None:
            initial_space = []
            for x in hint:
                # Read only eigenfuction
                with x.dat.vec_ro as y:
                    initial_space.append(y.copy())
            eps.setInitialSpace(initial_space)

        eps.solve()
        eigenvalues = []
        eigenfunctions = []
        eigenfunction = Function(V, name="Eigenfunction")

        for i in range(eps.getConverged()):
            lmbda = eps.getEigenvalue(i)
            assert lmbda.imag == 0
            eigenvalues.append(lmbda.real)
            with eigenfunction.dat.vec_wo as x:
                eps.getEigenvector(i,x)
            eigenfunctions.append(eigenfunction.copy(deepcopy=True))

        if min(eigenvalues) < 0:
            is_stable = False
        else:
            is_stable = True

        d = {"stable": is_stable,
             "eigenvalues": eigenvalues,
             "eigenfunctions": eigenfunctions,
             "hint": eigenfunctions}

        return d

    def estimate_error(self, *args, **kwargs):
        return estimate_error_dwr(self, *args, **kwargs)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parameter parser script")

    # Define arguments with types and defaults
    parser.add_argument("-n", type=int, default=2, help="Integer parameter n")
    parser.add_argument("--r-coef", type=float, default=0.9, help="Float coefficient r_coef")
    parser.add_argument("--lmbda0", type=float, default=0.1, help="Float parameter lmbda0")

    args = parser.parse_args()

    # Access parsed values
    n = args.n
    r_coef = args.r_coef
    lmbda0 = args.lmbda0

    problem=HyperelasticityProblem(n=n, r_coef=r_coef)
    dc = DeflatedContinuation(problem=problem, teamsize=1, verbose=True, clear_output=True)

    params = list(arange(0, 3e-2, 0.005))+list(arange(3e-2, 5e-2, 0.001))+list(arange(5e-2, lmbda0+0.0001, 0.0001))
    dc.run(values={"eps": params})

    old_path = find_matching_subfolder(REPO_ROOT / "output", lmbda0, tol=1e-6) # check that REPO_ROOT/"output" is indeed that path to the defcon output
    path=REPO_ROOT / f"data/initial_solutions/n{n}_2d"
    if os.path.exists(path):
        # Do not delete the checkpoints shipped with the repository: defcon does not
        # guarantee stable branch numbering across runs, so the previous contents are
        # the only reference for identifying which branch is which. Move them aside.
        backup = path.with_name(f"{path.name}.superseded_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        os.rename(path, backup)
        print(f"Existing initial data moved to {backup}")
    os.rename(old_path,path)
    print(f"New initial data written to {path}")
