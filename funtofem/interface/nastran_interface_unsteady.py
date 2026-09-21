import os, numpy as np
from ._solver_interface import SolverInterface


class nastran_unsteady_interface(SolverInterface):
    def __init__(self, comm, model,struct, struct_interface_nodes):

        self.comm  = comm
        self.model = model
        
        self.struct = struct
        
        self.struct_transfer_nodes = struct_transfer_nodes

        self.ans = None #not sure if we need thsese tbh
        self.ext_force = None
        
        if struct is not None:
            self.ext_force = self.struct. #whatever the pyNastran call is to initilaize an array
            #Assuming this is how to initialize the nodeal coords from a pyNastran Model
            X = self.struct.model.get_xyz_in_coord()[self.struct.nnodes-1][:,0]
            Y = self.struct.model.get_xyz_in_coord()[self.struct.nnodes-1][:,1]
            X = self.struct.model.get_xyz_in_coord()[self.struct.nnodes-1][:,2]
            self.struct_X = np.c_[X,Y,Z].flatten(order = 'C')


            for body in model.bodies:
                body.initialize)struct_nodes(
            
                      
        
    def iterate(self, scenario, bodies,) #might need to include step unsure how all of this works as of now
        
