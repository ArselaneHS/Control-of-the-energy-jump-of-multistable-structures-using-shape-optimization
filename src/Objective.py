from firedrake import *
from fireshape import *
from pyadjoint.adjfloat import AdjFloat
import firedrake.adjoint as fda

import shutil
import os
import numpy as np
from pathlib import Path
from src.utils.paths import make_results_path_from_objective, ensure_dir
from firedrake.petsc import PETSc

from slepc4py import SLEPc


from src.initialisation_utils.get_initial_data import initialize_mesh


class EnergyJumpControl(PDEconstrainedObjective):
    def __init__(self, Q, objective_params,write=True, snes_max_it=150., results_path=None, dim=2, *args, **kwargs):
        """
        Parameters
        ----------
        Q: FeControlSpace - function space for the control.
        bottom, top: int -  boundary labels for DirichletBCs.
        lmbda0: float - vertical displacement at the top boundary.
        N_holes: int - number of holes in the domain.
        N_solutions: int - number of solutions to compare.
        path: string - path to the solutions.
        path_solutions: list of strings - names of the solutions considered.
        i1, i2: list of ints - indices of the solutions in path_solutions to compare.
        p: float - percentage of the target reduction of the energy jump .
        """
        super().__init__(Q, *args, **kwargs)

        # Set up objective parameters
        objective_params["number of solutions"] = len(objective_params["path_solutions"])
        self.objective_params=objective_params
        self.qdegree=None if dim==2 else 4
        self.snes_max_it=snes_max_it
        self.dim=dim
        self.write = write
        self.p_float = objective_params["percentage"][0] if isinstance(objective_params["percentage"], list) else objective_params["percentage"]
        assert len(self.objective_params["i1"]) == len(self.objective_params["i2"])
        assert self.objective_params["number of solutions"] > 1


        # save objective_params into a text file
        if results_path is None:
            results_path = str(make_results_path_from_objective(objective_params, NE=0))
            shutil.rmtree(results_path, ignore_errors=True)
            os.makedirs(results_path, exist_ok=True)
        save_objective_params(results_path=results_path, objective_params=objective_params, snes_max_its=snes_max_it)
        
        
        # Create function space
        self.Q = Q
        self.mesh=Q.mesh_m

        # Create function space for the solutions
        CG_degree = None
        with CheckpointFile(str(Path(self.objective_params["path"]) / self.objective_params["path_solutions"][0]), mode='r') as afile:
            meshh = afile.load_mesh('firedrake_default')
            temp = afile.load_function(meshh, 'solution')
            CG_degree = temp.ufl_element().degree() 
        CG_degree = CG_degree[0] if isinstance(CG_degree, tuple) else CG_degree
        self.V = VectorFunctionSpace(self.mesh, "CG", CG_degree)

        # Create function that stores the solutions
        self.u  = [Function(self.V,name=f"u_{i+1}") for i,_ in  enumerate(self.objective_params["path_solutions"])]
        self.up = [Function(self.V,name=f"u_{i+1}_") for i,_ in  enumerate(self.objective_params["path_solutions"])]

        self.initialize_solutions()


        # create boundary conditions and test function
        self.v= TestFunction(self.V)
        bottom = (0.0,) * self.dim
        top = list(bottom); top[1] = -self.objective_params["top displacement"]
        bc1 = DirichletBC(self.V, Constant(bottom), self.objective_params["bottom"])
        bc2 = DirichletBC(self.V, Constant(tuple(top)), self.objective_params["top"])
        self.bcs = [bc1,bc2]

        # Create pvd file and Callback function
        pvd_file = VTKFile(Path(results_path)/"solution/u.pvd") if self.write else None
        self.flags = []
        def cb_(flag=None, *args, **kwargs):
            self.flags.append(flag)
            if pvd_file is not None:
                pvd_file.write(*(self.u))
        self.cb = cb_


        # Compute the initial objective value
        self.p=Constant(self.p_float)
        self.delta_psi=[self.energy(self.u[i])-self.energy(self.u[j]) for i,j in zip(self.objective_params["i1"],self.objective_params["i2"])]
        
        self.assemble_kwargs = {"form_compiler_parameters": {"quadrature_degree": self.qdegree}} if self.qdegree is not None else {}
        self.deltas0=[(float((assemble(delta_psi*dx, **self.assemble_kwargs)))) for delta_psi in self.delta_psi]
       
        self.obj0 = (1 - self.p_float) ** 2 * len(self.deltas0)
        self.pen0=sum([float((norm(self.u[i]-self.u[j])**2)**(-1)) for i in range(self.objective_params["number of solutions"]) for j in range(i+1,self.objective_params["number of solutions"])])

        print("===============================================")
        print("Objective Function:")
        print("Parameters:")
        for key, value in self.objective_params.items():
            print(f"  {key}: {value}")
        print("Initial objective value:", self.obj0)
        print("Initial energy jumps:", self.deltas0)
        print("===============================================")

    def initialize_solutions(self):
        V=self.u[0].function_space()
        for i,solution_path in enumerate(self.objective_params["path_solutions"]):
            solution_file = Path(self.objective_params["path"]) / solution_path
            with CheckpointFile(str(solution_file), mode='r') as afile:
                meshh = afile.load_mesh('firedrake_default')
                temp = afile.load_function(meshh, 'solution')
                if temp.function_space().mesh() != self.u[i].function_space().mesh():
                    try:
                        temp = project(temp, self.u[i].function_space())
                        self.u[i].assign(temp)
                    except:
                        self.u[i].dat.data[:] = temp.dat.data[:] 
                self.up[i].assign(self.u[i])

    def residual(self,u,v):
        if self.qdegree is None:
            return  derivative(self.energy(u)*dx, u, v) 
        else:
            return derivative(self.energy(u)*dx(metadata={"quadrature_degree": self.qdegree}), u, v)




    def psi(self, u):
        """ Strain energy density (compressible neo-Hookean model). """

        # Kinematics
        I = Identity(self.dim)        # Identity tensor matching the spatial dimension
        F = I + grad(u)             # Deformation gradient
        C = F.T*F                   # Right Cauchy-Green tensor

        # Invariants of deformation tensors
        Ic = tr(C)
        J  = det(F)

        # Elasticity parameters
        E, nu = 1000000.0, 0.3
        mu, lmbda_cte = Constant(E/(2*(1 + nu))), Constant(E*nu/((1 + nu)*(1 - 2*nu)))

        # Stored strain energy density (compressible neo-Hookean model)
        psi = (mu/2)*(Ic - self.dim) - mu*ln(J) + (lmbda_cte/2)*(ln(J))**2

        return psi

    def energy(self, u):
        """ Energy function. """
        # Body force per unit volume
        if self.dim==2:
            B   = Constant((0.0, -1000))
        else:
            B   = Constant((0.0, -1000, 0.0))

        psi=self.psi(u)
        # Total potential energy
        Energy = psi- dot(B, u)

        return Energy
    
    def solver_parameters(self):
        solver_parameters = {
            "snes_max_it": self.snes_max_it,
            "snes_linesearch_type": "l2",
         }
        return solver_parameters

    def solve_pdes(self):
        """ Solve PDE constrained. """
        # assign initial values
        [uk.assign(ukp) for uk, ukp in zip(self.u, self.up)]

        # solve PDEs
        for i, uk in enumerate(self.u):
            solve(self.residual(uk,self.v)==0, uk, self.bcs, solver_parameters=self.solver_parameters())
        
        # update previous solutions
        [ukp.assign(uk) for uk, ukp in zip(self.u, self.up)] 
    
    def evaluate_objective(self):
        """ Evaluate objective function. """
        # NOTE: The objective implemented here equals the paper's objective divided
        # by r^2 (p**2 in the code). This is because experiment 4 uses a continuation
        # strategy in which p is updated dynamically, but because p is defined within the tape
        # it must be a firedrake.Constant appearing inside the integral rather than a fixed scalar factor outside it.
        # The objective values that are saved and plotted are rescaled to match the
        # paper's definition. Using the paper's expression directly gives identical
        # results, except that experiment 4 cannot run (p would not be updated).        

        # evaluate objective
        deltas = [assemble((1 / self.p) * (self.energy(self.u[i]) - self.energy(self.u[j])) * dx, **self.assemble_kwargs)
            for i, j in zip(self.objective_params["i1"], self.objective_params["i2"])]
        obj = sum((delta/delta0-1)**2 for delta, delta0 in zip(deltas, self.deltas0))

        pen = sum((norm(self.u[i] - self.u[j])**2)**(-1) for i in range(self.objective_params["number of solutions"]) 
              for j in range(i + 1, self.objective_params["number of solutions"])) / self.pen0

        return (obj) +self.objective_params["coef_pen"]*pen
    
    def save_results(self):
        ### This is messy but it is the only way I managed to keep track of the results with the tape and co ###
        U = [fda.Control(u).tape_value() for u in self.u]
        energies = {rf"$\mathcal{{E}}({u.name()})$": [] for u in self.u}
        deltas = {
            rf"$\Delta\mathcal{{E}}({u.name()},{v.name()})$": []
            for i, u in enumerate(self.u)
            for j, v in enumerate(self.u)
            if j > i
        }
        objs = []

        psi_func = self.energy
        i1 = self.objective_params["i1"]
        i2 = self.objective_params["i2"]
        deltas0 = self.deltas0
        p_const = self.p
        assemble_kwargs = self.assemble_kwargs

        ### "self" can not be used inside "fun" or it breaks the tape ###
        def fun(self_obj, J_val, *args):
            for u in U:
                energies[rf"$\mathcal{{E}}({u.name()})$"].append(
                    assemble(psi_func(u) * dx, **assemble_kwargs)
                )

            for i, u in enumerate(U):
                for j, v in enumerate(U):
                    if j > i:
                        e_u = energies[rf"$\mathcal{{E}}({u.name()})$"][-1]
                        e_v = energies[rf"$\mathcal{{E}}({v.name()})$"][-1]
                        deltas[rf"$\Delta\mathcal{{E}}({u.name()},{v.name()})$"].append(
                            float((e_u - e_v))
                        )

            D = [
                (1 if i < j else -1) * deltas[rf"$\Delta\mathcal{{E}}({U[min(i,j)].name()},{U[max(i,j)].name()})$"][-1]
                for i, j in zip(i1, i2)
            ]
            p_now = float(p_const)
            inner_obj = sum((delta / delta0 - p_now) ** 2 for delta, delta0 in zip(D, deltas0))
            objs.append(inner_obj)

            return {"energies": energies, "deltas": deltas, "objs": objs}        
        return fun
        

    def objective_value(self):
        """ Solve PDE constrained and evaluate reduce function. """
        
        # solve PDEs
        self.solve_pdes()

        # compute objecttive
        obj = self.evaluate_objective()

        # Save results
        self.eval_cb_post= self.save_results()

        return (obj)

def save_objective_params(results_path, objective_params, snes_max_its=None, filename="objective_params.txt"):
    """Save the parameters of objective_params into a text file."""
    p = Path(results_path)
    ensure_dir(p)
    params_path = p / filename
    with params_path.open('w') as file:
        file.write("Objective Parameters:\n")
        for key, value in objective_params.items():
            file.write(f"{key}: {value}\n")
        file.write(f"snes_max_its: {snes_max_its}\n")

def make_results_directory(objective_params, NE=0):
    """Compatibility wrapper for the centralized timestamped results directory."""
    from src.utils.paths import make_results_directory as _make_results_directory
    return _make_results_directory(objective_params, NE=NE)

def make_objective(
    objective_params, write=True, snes_max_it=50, results_path=None, *args, **kwargs
):
    """Factory function initialization setting up domains, spaces, controls, and objectives."""
    from src.utils.paths import resolve_path

    n_holes = objective_params["number of holes"]
    r_coef = objective_params["radius"]

    objective_params_path = resolve_path(
        objective_params.get("path", "data/initial_solutions")
    )
    objective_params["path"] = str(objective_params_path)
    checkpoint_file = str(objective_params_path / objective_params["path_solutions"][0])

    mesh, bottom, top = initialize_mesh(
        N_holes=n_holes,
        r_coef=r_coef,
        height=objective_params.get("height", None),
        checkpoint_file=checkpoint_file,
    )
    objective_params["bottom"] = bottom
    objective_params["top"] = top

    Q = FeControlSpace(mesh)
    q = ControlVector(Q, H1InnerProduct(Q, fixed_bids=top + bottom))
    dim = 2 if objective_params.get("height", None) is None else 3

    J = EnergyJumpControl(
        Q,
        objective_params,
        write=write,
        results_path=results_path,
        snes_max_it=snes_max_it,
        dim=dim,
    )
    return J, q, Q