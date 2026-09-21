import numpy as np
from pyfuntofem.driver import SolverInterface
from funtofem import TransferScheme
import os

class NastranInterface(SolverInterface):
    """
    An structural solver interface for Nastran based on file I/O

    Assumptions:
       - there is a single body in the model
       - Nastran is going to be run from the command line

    Parameters
    ----------
    comm: MPI Comm
        global MPI communicator
    struct_comm: MPI Comm
        structural MPI communicator
    model: :class:`~funtofem_model.FUNtoFEMmodel`
        FUNtoFEM model with the problem definition. The modal solver instantiation will fill in body.struct_X

    """
    def __init__(self,comm,struct_comm,model):

        self.comm = comm
        self.struct_comm = struct_comm

        if self.comm.Get_rank()==0:
            model.bodies[0].struct_X = self.get_mesh()
            model.bodies[0].struct_nnodes = model.bodies[0].struct_X.size/3
        else:
            model.bodies[0].struct_nnodes = 0
            model.bodies[0].struct_X = np.zeros(model.bodies[0].struct_nnodes*3,dtype=TransferScheme.dtype)

        model.bodies[0].struct_disps = np.zeros(model.bodies[0].struct_nnodes*3,dtype=TransferScheme.dtype)

    def iterate(self,scenario,bodies,step):
        """
        Update the structural solution

        Parameters
        ----------
        scenario: :class:`~scenario.Scenario`
            The current scenario
        bodies: list of :class:`~body.Body` objects
            The bodies in the model
        """
        if self.comm.Get_rank()==0:
            matrix = np.zeros((bodies[0].struct_loads.size/3,6))
            matrix[:,0] = bodies[0].struct_X[0::3]
            matrix[:,1] = bodies[0].struct_X[1::3]
            matrix[:,2] = bodies[0].struct_X[2::3]
            matrix[:,3] = bodies[0].struct_loads[0::3]
            matrix[:,4] = bodies[0].struct_loads[1::3]
            matrix[:,5] = bodies[0].struct_loads[2::3]
            np.savetxt('struct_loads.dat',matrix)

            self.write_forces(bodies[0].struct_loads)
            self.run_nastran(step)
            bodies[0].struct_disps = self.get_displacements()


        return 0

    def get_mesh(self):
        """
        Return the vector of structural node locations [x1,y1,z1,x2,y2,z2,...]
        """

        # Read the coordinates
        mesh_file = 'SOL101_no_conn.dat'

        matrix = np.loadtxt(mesh_file)

        self.funofem_ids = np.array(matrix[:,3],dtype=int)
        struct_x = matrix[:,:3].flatten()

        self.struct_nnodes = len(self.funtofem_ids)

        return struct_X

    def write_forces(self,struct_loads):
        """
        Write the force vector for nastran
        struct_loads is the vector [fx1,fy1,fz1,fx2,fy2,fz2,...]
        """
        file_name = "force_file.bdf"

        fh = open(file_name,'w')

        fh.write('$   LOAD = 215\n')

        for i,id in enumerate(self.funtofem_ids):
            f = struct_loads[3*i:3*i+3]
            # write the positive half

            idstr = '%8d' % id

            s1 = self.force_string(f[0])
            s2 = self.force_string(f[1])
            s3 = self.force_string(f[2])
            string = 'FORCE   '+' 216    '+idstr+' 0      '+'  1.    '+s1+s2+s3 + '\n'
            if not ("0.0      0.0    0.0" in string or
                    "0.0     0.0     0.0" in string):
                fh.write(string)

        # write self.ids[i]  and force to load
        fh.write('LOAD    215     1.      1.      216')
        fh.close()

    def force_string(self,f):
        if abs(f) < 1e-10:
            st = '0.0     '
        elif f < 0.01 and f> 0.0:
            st1 = '%1.4e' % f
            if int(st1[-2:])<10:
                st1 = st1[:-2]+st1[-1]
            st = st1.replace('e','')
        elif f > 9.9:
            st1 = '%1.4e' % f
            if int(st1[-2:])<10:
                st1 = st1[:-2]+st1[-1]
            st = st1.replace('e','')
        elif f > 0.0:
            st = '%8f' % f
        elif f > -0.01: #negative exponents
            st1 = '%1.3e' % f
            if int(st1[-2:])<10:
                st1 = st1[:-2]+st1[-1]
            st = st1.replace('e','')
        elif f < -9.9: #negative exponents
            st1 = '%1.3e' % f
            if int(st1[-2:])<10:
                st1 = st1[:-2]+st1[-1]
            st = st1.replace('e','')
        else: # negative full numbers
            st = '%1.5f' % f
        return st

    def run_nastran(self,step):
        os.system("touch fun3d_done")
        while not os.path.isfile('nastran_done'):
            os.system("sleep 1")
        os.system("rm nastran_done")

    def get_displacements(self):
        """
        Return the vector of structural displacements [dx1,dy1,dz1,dx2,dy2,dz2,...]
        """
        file_name = 'SOL101.f06'
        fh = open(file_name)

        ids = []
        disps = []

        struct_disps = np.zeros(self.struct_nnodes*3)
        count = 0
        while True:
            line = fh.readline()
            if 'D I S P L A C E M E N T' in line:
                line = fh.readline()
                line = fh.readline()
                while True:
                    line = fh.readline()
                    if line[0] == '1':
                        break
                    id = int(line[6:14])
                    if id in self.funtofem_ids:
                        i = np.where(self.funtofem_ids(self.funtofem_ids==id))[0][0]
                        disps = np.array([float(line[26:39]), float(line[41:54]), float(line[56:69])])
                        struct_disps[3*i:3*i+3] = disps
                        count += 1
            elif not line:
                break
        print 'NASTRAN: number of disps set', count,self.struct_nnodes

        return struct_disps

