import firedrake as fd
from fireshape import FeControlSpace

class CG1ControlSpace(FeControlSpace):
    def __init__(self, mesh_r):
        self.mesh_r = mesh_r
        self.V_r = fd.VectorFunctionSpace(self.mesh_r, "CG", 1)
        self.V_r_dual = self.V_r.dual()

        X = fd.SpatialCoordinate(self.mesh_r)
        self.id = fd.assemble(fd.interpolate(X, self.V_r))
        self.T = fd.Function(self.V_r, name="T")
        self.T.assign(self.id)
        self.mesh_m = fd.Mesh(self.T)
        self.V_m = fd.VectorFunctionSpace(self.mesh_m, "CG", 1)
        self.V_m_dual = self.V_m.dual()
