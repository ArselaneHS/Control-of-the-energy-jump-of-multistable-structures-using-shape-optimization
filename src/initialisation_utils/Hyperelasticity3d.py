
# VTKFile("test.pvd").write(u)
from firedrake import *
from netgen.occ import *
import matplotlib.pyplot as plt
import time
from src.utils.paths import get_solutions_paths
import os
import numpy as np

from pathlib import Path
import argparse

# Path to the directory containing this script
SCRIPT_DIR = Path(__file__).resolve().parent

# REPO_ROOT = SCRIPT_DIR / "../.." resolved to an absolute path
REPO_ROOT = (SCRIPT_DIR / "../..").resolve()

def mesh2d(n,r_coef=0.9):
        # Recreat boundary labels
        rect = WorkPlane(Axes((0,0,0), n=Z, h=X)).Rectangle(1,1).Face().bc("sides")
        rect.edges.Min(Y).name = "bottom"
        rect.edges.Max(Y).name = "top"

        n=n+1
        r=r_coef*(1/(2*(n)))
        shape = rect
        for i in range(1, n):
                for j in range(1, n+2):
                        centre_x = (1/n) * (j-1)
                        centre_y = (1/n) * (i+0)
                        disk = WorkPlane(Axes((centre_x, centre_y, 0), n=Z, h=X)).Circle(r).Face()
                        shape = shape - disk
                
        geo = OCCGeometry(shape, dim=2)
        ngmesh = geo.GenerateMesh(maxh=1)

        mesh = Mesh(ngmesh, dim=2)
        mh = MeshHierarchy(mesh, 2, netgen_flags={})
        mesh = mh[-1]
        bottom = [i + 1 for (i, name) in enumerate(ngmesh.GetRegionNames(codim=1)) if name == "bottom"]
        top = [i + 1 for (i, name) in enumerate(ngmesh.GetRegionNames(codim=1)) if name == "top"]

        return mesh, bottom, top


def mesh(n, r_coef=None, height=None):
        rect = WorkPlane(Axes((0,0,0), n=Z, h=X)).Rectangle(1,1).Face().bc("sides")
        if height is None:
                rect.edges.Min(Y).name = "bottom"
                rect.edges.Max(Y).name = "top"

        n=n+1
        if r_coef is None:
                r_coef = 0.9
        shape = rect
        for i in range(1,n):
                for j in range(1, n+2):
                        centre_x = (1/n)*(j-1)
                        centre_y = (1/n)*(i+0)
                        disk = WorkPlane(Axes((centre_x, centre_y, 0), n=Z, h=X)).Circle(r_coef*(1/(2*n))).Face()
                        shape = shape - disk
        if height is not None:
                shape = shape.Extrude(height)
                shape.faces.Min(Y).name = "bottom"
                shape.faces.Max(Y).name = "top"
                shape.faces.Min(Z).name = "side"
                shape.faces.Min(X).name = "left"

        geo = OCCGeometry(shape, dim= 2 if height is None else 3)
        ngmesh = geo.GenerateMesh(maxh=0.05)
        coarse_mesh = Mesh(ngmesh, dim=3, maxh=0.05)

        bottom = [i + 1 for (i, name) in
                enumerate(ngmesh.GetRegionNames(codim=1)) if name == "bottom"]
        top    = [i + 1 for (i, name) in
                enumerate(ngmesh.GetRegionNames(codim=1)) if name == "top"]
        side    = [i + 1 for (i, name) in
                enumerate(ngmesh.GetRegionNames(codim=1)) if name == "side"]
        return coarse_mesh, bottom, top, side

def equation(u,v,dim=2, qdegree=6):
        # Material parameters (Lamé parameters)
        E, nu = 1000000.0, 0.3

        mu = E / (2*(1 + nu))
        lmbda = E*nu/((1 + nu)*(1 - 2*nu))

        # Define kinematics
        I = Identity(dim)
        F = I + grad(u)
        C = F.T * F
        J = det(F)

        # Define strain energy density (Neo-Hookean)
        psi = (mu/2)*(tr(C) - dim) - mu*ln(J) + (lmbda/2)*(ln(J))**2

        # Step 4: Define total potential energy
        B   = Constant((0.0, -1000, 0.0)) if dim == 3 else Constant((0.0, -1000))  # Body force


        energy = psi * dx(metadata={"quadrature_degree": qdegree})  - dot(B, u) * dx(metadata={"quadrature_degree": qdegree})  # Total potential energy

        # Step 5: Compute residual and Jacobian
        F_form = derivative(energy, u, v)
        J_form = derivative(F_form, u)
        return F_form, J_form

def solver_params(dim=2):
        solver_parameters ={
                "snes_monitor": None,
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
                "mat_mumps_icntl_22": 1,    # out-of-core: factors to disk. 6219 MB -> 860 MB in core
                "mat_mumps_icntl_7": 2,     # AMF ordering: best OOC working space measured here
               }

        return solver_parameters


def Initial_guess(file, V, top, bottom, base_2dmesh):
        mesh = V.mesh()
        R=VectorFunctionSpace(mesh, 'CG', 2, vfamily='Real', vdegree=0)
        uR=Function(R)

        with CheckpointFile(file, 'r') as afile:
            meshh = afile.load_mesh('firedrake_default')
            temp = afile.load_function(meshh, 'solution')
            temp=project(temp, VectorFunctionSpace(base_2dmesh, 'CG', 2))
        
        uR.dat.data[:] =  [np.concatenate((temp.dat.data[i],np.array([0]))) for i in range(len(temp.dat.data))]
        u = Function(V). interpolate(uR)

        return u                


def solver(problem, solver_params, prefix="", **kwargs):
        firedrake_solver_args = ['nullspace', 'transpose_nullspace', 'appctx', 'pre_jacobian_callback', 'post_jacobian_callback', 'pre_function_callback', 'post_function_callback']
        valid_kwargs = {key: value for (key, value) in kwargs.items() if key in firedrake_solver_args}
        valid_kwargs["pre_apply_bcs"] = False # impose BCs like FEniCS
        return NonlinearVariationalSolver(
                problem, options_prefix=prefix,
                solver_parameters=solver_params,
                **valid_kwargs
                )

if __name__ == "__main__":
        parser = argparse.ArgumentParser(description="Parameter parser script")

        # Define arguments with types and defaults
        parser.add_argument("-n", type=int, default=2, help="Integer parameter n")
        parser.add_argument("--r-coef", type=float, default=0.9, help="Float coefficient r_coef")
        parser.add_argument("--lmbda0", type=float, default=0.1, help="Float parameter lmbda0")

        args = parser.parse_args()

        # Access parsed values
        n = args.n
        r = args.r_coef

        dim=3
        qdegree = 6


        base_2dmesh, bottom, top = mesh2d(n=n, r_coef=r)
        base_2dmesh.name = "mesh2d"
        mesh3d=ExtrudedMesh(base_2dmesh, 6, name="firedrake_default")

        base_path = f"{REPO_ROOT}/data/initial_solutions/n{n}_2d/" 
        paths_solutions=get_solutions_paths(base_path)

        CG_degree = None
        with CheckpointFile(str(Path(base_path) / paths_solutions[0]), mode='r') as afile:
            meshh = afile.load_mesh('firedrake_default')
            temp = afile.load_function(meshh, 'solution')
            CG_degree = temp.ufl_element().degree() 

        V= VectorFunctionSpace(mesh3d, "CG", CG_degree)
        v = TestFunction(V)

        solver_parameters = solver_params(dim=dim)


        U=[Function(V, name=solution) for solution in paths_solutions]

        bc1 = DirichletBC(V,Constant((0.0,  -0.1, 0.0)), top)
        bc2 = DirichletBC(V,Constant(( 0.0, 0.0, 0.0)), bottom)
        
        save_path = f"{REPO_ROOT}/data/initial_solutions/n{n}_3d/"
        os.makedirs(save_path, exist_ok=True)
        for (i,solution) in enumerate(paths_solutions):
                print("------- solution:", solution)
                print("Initialization")
                u_=Initial_guess(base_path+solution, V, top, bottom, base_2dmesh)
                u = Function(V, name=solution[-3])
                u.assign(u_)

                F_form, J_form = equation(u,v, dim=dim, qdegree=qdegree)
                problem = NonlinearVariationalProblem(F_form, u, J=J_form, bcs=[bc1, bc2])

                time0 = time.time()
                # s = solver(problem, solver_parameters, transfer_manager=tm)
                print("Solving")

                try:
                        s = solver(problem, solver_parameters)
                        s.solve()
                        U[i].assign(u)
                        print(U[i].name())
                        name='solution'
                        with CheckpointFile(save_path+solution, 'w') as afile:
                                afile.save_mesh(mesh3d)
                                afile.save_function(U[i], name=name)
                        with CheckpointFile(save_path+solution, 'r') as afile:
                                meshh = afile.load_mesh('firedrake_default')
                                temp = afile.load_function(meshh, name)
                except:
                        print("Solver failed for", solution)
                        continue
                time1 = time.time()
                print("Solve time:", time1-time0)

        # VTKFile("test2.pvd").write(*U)
