"""Print branch-identification descriptors for every checkpoint in a directory.

Usage:
    python3 -m src.utils.identify_branches data/initial_solutions/n2_2d

For each solution-<k>.h5 prints the total potential energy (the quantity the
objective is built from), the mean horizontal displacement, the first moment
M1 = int u_x (y - 1/2) dx, and the two defcon functionals (which reproduce the
functional-<k>.txt files that defcon writes). Mean u_x and M1 flip sign under
the reflection x -> 1 - x and vanish for a mirror-symmetric branch. README
section 6.4 explains how to map these onto u_1, u_2, u_3.
"""
import re
import sys

from firedrake import *

from src.Objective import total_potential_energy
from src.utils.paths import get_solutions_paths, resolve_path


def main(directory):
    directory = resolve_path(directory)
    files = sorted(get_solutions_paths(str(directory)),
                   key=lambda f: int(re.search(r"-(\d+)", f).group(1)))
    print(f"{'file':<16}{'E_total':>14}{'mean u_x':>13}{'M1':>13}{'tvd(defcon)':>14}{'pointeval':>13}")
    for name in files:
        with CheckpointFile(str(directory / name), 'r') as afile:
            mesh = afile.load_mesh('firedrake_default')
            u = afile.load_function(mesh, 'solution')
        dim = u.ufl_shape[0]
        # Same quadrature choice as EnergyJumpControl, so 3-D energies match its printout.
        kw = {"form_compiler_parameters": {"quadrature_degree": 4}} if dim == 3 else {}
        x = SpatialCoordinate(mesh)
        vol = assemble(Constant(1.0) * dx(mesh))
        E = float(assemble(total_potential_energy(u, dim) * dx, **kw))
        ux = float(assemble(u[0] * dx)) / vol
        M1 = float(assemble(u[0] * (x[1] - 0.5) * dx))
        tvd = float(assemble(u[1] * dx)) / 0.1                  # defcon's definition
        p = (0.25, 0.05) if dim == 2 else (0.25, 0.05, 0.5)
        pt = float(u(p)[1])
        print(f"{name:<16}{E:>14.4f}{ux:>13.3e}{M1:>13.3e}{tvd:>14.6f}{pt:>13.3e}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
