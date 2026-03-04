import sys
import os
# import torch
# from torch.autograd import Variable
import numpy as np
import math
from scipy.spatial import KDTree
# from sklearn.decomposition import PCA


fileAbsPath = os.path.abspath(os.path.dirname(__file__))
algorithmPath = os.path.dirname(fileAbsPath)
sys.path.append(fileAbsPath)
sys.path.append(algorithmPath)

# import algLinearMath
# import algGeometry
import Algorithm.scoUtil as scoUtil
import Algorithm.scoBuffer as scoBuffer
import Algorithm.scoBufferAlg as scoBufferAlg


class CSegmentBasedVoxelProcess :
    def __init__(self) -> None :
        self.m_anchor = None
        self.m_anchorSegInx = []
        self.m_npAnchorSegInx = None
        self.m_npNNIndex = None

        self.m_queryVertex = None
        self.m_npQuerySegInx = None

    def add_anchor(self, anchorVertex : np.ndarray, segInx : int) :
        if self.m_anchor is None :
            self.m_anchor = np.copy(anchorVertex)
        else :
            self.m_anchor= np.concatenate((self.m_anchor, anchorVertex), axis=0)
        self.m_anchorSegInx += [segInx for i in range(0, anchorVertex.shape[0])]
    def process(self, queryVertex : np.ndarray) :
        self.m_queryVertex = queryVertex
        self.m_npAnchorSegInx = np.array(self.m_anchorSegInx)

        print("kd-tree build start")
        tree = KDTree(self.m_anchor)
        print("kd-tree build complete")
        distances, self.m_npNNIndex = tree.query(queryVertex, k=1)
        self.m_npQuerySegInx = self.m_npAnchorSegInx[self.m_npNNIndex]
        print("completed segment")
    
    def get_query_vertex_with_seg_index(self, segInx : int) :
        indices = np.where(self.m_npQuerySegInx == segInx)
        return self.m_queryVertex[indices]
    

