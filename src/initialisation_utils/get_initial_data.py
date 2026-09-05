import os
from firedrake import *
from fireshape import *
from netgen.occ import *
import re
import numpy as np

from src.utils.paths import get_solutions_paths, get_optimum_solutions_paths

def initialize_mesh(N_holes,r_coef=0.9, height=None, checkpoint_file=None):
    """
    Initializes a 2D rectangular mesh with a specified number of circular holes and boundary labels,
    and optionally extrudes it to 3D.

    Parameters
    ----------
    N_holes : int
        The number of holes to create in the mesh. The holes are arranged in a grid pattern.
    r_coef : float, optional
        The relative radius of each hole (default is 0.9). If 0, holes are points; if 1, holes are in contact.
    height : int or float, optional
        If provided, the mesh is extruded to 3D with the given height.

    Returns
    -------
    mesh : Mesh or ExtrudedMesh
        The generated Firedrake mesh (2D or extruded 3D).
    bottom : list of int
        List of boundary indices corresponding to the bottom edge/face of the mesh.
    top : list of int
        List of boundary indices corresponding to the top edge/face of the mesh.

    Notes
    -----
    - The function uses Netgen/NGSolve geometry tools to construct the mesh.
    - Holes are distributed evenly within the rectangle, and half holes along the left and right boundary.
    - Boundary labels "bottom" and "top" are assigned for later use in boundary conditions.
    - If `height` is specified, the mesh is extruded in the third dimension.
    """



    rect = WorkPlane(Axes((0,0,0), n=Z, h=X)).Rectangle(1,1).Face().bc("sides")
    rect.edges.Min(Y).name = "bottom"
    rect.edges.Max(Y).name = "top"

    n = N_holes + 1
    shape = rect
    for i in range(1,n):
        for j in range(1, n+2):
            centre_x = (1/n)*(j-1)
            centre_y = (1/n)*(i+0)
            disk = WorkPlane(Axes((centre_x, centre_y, 0), n=Z, h=X)).Circle(r_coef*(1/(2*n))).Face()
            shape = shape - disk

    geo = OCCGeometry(shape, dim=2)
    ngmesh = geo.GenerateMesh(maxh=1)
    meshh = Mesh(ngmesh)
    mh = MeshHierarchy(meshh, 2, netgen_flags={})
    meshh = mh[-1]


    bottom = [i + 1 for (i, name) in enumerate(ngmesh.GetRegionNames(codim=1)) if name == "bottom"]
    top = [i + 1 for (i, name) in enumerate(ngmesh.GetRegionNames(codim=1)) if name == "top"]

    if height is not None:
        mesh = ExtrudedMesh(meshh, height)
    
    if checkpoint_file is not None:
        with CheckpointFile(checkpoint_file, 'r') as afile:
            mesh = afile.load_mesh('firedrake_default')
    else:
        mesh = meshh

    return mesh, bottom, top

def initialize_solutions(mesh,path,keep_all):

    """
    Initializes the list of solution paths and selects indices for optimization.

    Parameters
    ----------
    mesh : Mesh
        The Firedrake mesh object used to evaluate solution energies.
    path : str
        Directory path containing the solution files.
    keep_all : bool
        If True, keep all solutions and use the indices of the minimum and maximum energy solutions.
        If False, only keep the minimum and maximum energy solutions.

    Returns
    -------
    path_solutions : list of str
        List of solution file names (all or just min/max, depending on keep_all).
    i1 : list of int
        List containing the index (or indices) of the minimum energy solution.
    i2 : list of int
        List containing the index (or indices) of the maximum energy solution.
    N_solutions : int
        Number of solutions considered (either all or just 2 if keep_all is False).

    Notes
    -----
    - Uses `get_solutions_paths` to find solution files in the specified directory.
    - Uses `get_optimum_solutions_paths` to identify the solutions with minimum and maximum energy.
    - If `keep_all` is False, only the min and max energy solutions are kept for further processing.
    """
    path_solutions=get_solutions_paths(path)
    u_min,u_max,i_min,i_max=get_optimum_solutions_paths(mesh,path,path_solutions)
    if keep_all:
        i1,i2,N_solutions=[i_min],[i_max],len(path_solutions)
    else:
        path_solutions=[u_min,u_max]
        i1,i2, N_solutions=[0],[1],2
    return path_solutions,i1,i2,N_solutions

    