import sys
import os
import numpy as np
from scipy import ndimage
from scipy.ndimage import binary_dilation
import shutil
import vtk
import subprocess

from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QPushButton, QWidget
from PySide6.QtCore import Qt
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileAppPath = os.path.dirname(fileAbsPath)
fileToolPath = os.path.dirname(fileAppPath)
fileCommonPipelinePath = os.path.dirname(fileToolPath)

sys.path.append(fileAbsPath)
sys.path.append(fileAppPath)
sys.path.append(fileToolPath)
sys.path.append(fileCommonPipelinePath)


import AlgUtil.algVTK as algVTK
import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algImage as algImage
import AlgUtil.algSkeletonGraph as algSkeletonGraph
import AlgUtil.algSegment as algSegment

import Block.optionInfo as optionInfo
import Block.niftiContainer as niftiContainer
import Block.reconstruction as reconstruction

import data as data
import dataGroup as dataGroup
import geometry as geometry

import commandInterface as commandInterface



"""
Multi Territory
- 2-pass territory 지원 
- class 계층 
    - CCommandMultiTerritory : 2-pass territory interface class
        - CCommandMultiTerritoryLabel : cl에 정의된 label별로 territory 추출
        - CCommandMultiTerritoryKnife : knife에 의애 절단 된 부분부터 territory 추출 
"""
class CCommandMultiTerritory(commandInterface.CCommand) :
    @staticmethod
    def get_segment_vertex_from_np_value(npImg : np.ndarray, value, dtype=np.float32) -> list :
        mask = (npImg == value)
        labeled, num_features = ndimage.label(mask)
        if num_features <= 1 :
            return None

        coords_list = []
        for label in range(1, num_features + 1) :
            coords = np.transpose(np.where(labeled == label)).astype(dtype)
            coords_list.append(coords)
        return coords_list
    @staticmethod
    def get_blob_boundary(npImg: np.ndarray, value, dtype=np.float32) -> np.ndarray :
        mask = npImg == value
        dilated = binary_dilation(mask)
        boundary = dilated & (~mask)
        coords = np.transpose(np.where(boundary)).astype(dtype)
        return coords
    
    
    def __init__(self, mediator):
        super().__init__(mediator)
        # input your code
        self.m_inputSkeleton = None
        self.m_inputTerriInfo = None
        self.m_inputCLMask = None
    def clear(self) :
        # input your code 
        self.m_inputSkeleton = None
        self.m_inputTerriInfo = None
        self.m_inputCLMask = None
        super.clear()
    def process(self) :
        pass

    
    # protected
    def _do_territory(self, listLabel : list, listVertex : list) -> list :
        '''
        - listLabel : label 리스트
        - listVertex : label에 해당되는 seed point 
        - ret : label당 territory 결과, vtkPolyData로 반환
        '''
        if len(listLabel) != len(listVertex) :
            print("failed territory : invalid size")
            return None
    
        '''
        key : anchorID
        value : vertex : np.ndarray (n x 3, int)
        '''
        dicAnchor = {}
        retListPolyData = []

        terriInfo = self.InputTerriInfo
        segmentProcess = algSegment.CSegmentBasedVoxelProcess()
        for inx, label in enumerate(listLabel) :
            anchorID = inx + 1
            vertex = listVertex[inx]
            vertex = np.round(algLinearMath.CScoMath.mul_mat4_vec3(terriInfo.InvMat, vertex)).astype(np.int32)
            segmentProcess.add_anchor(vertex, anchorID)
            dicAnchor[anchorID] = vertex
            retListPolyData.append(None)
        segmentProcess.process(terriInfo.QueryVertex)

        npImg = algImage.CAlgImage.create_np(terriInfo.OrganInfo[4], np.uint8)
        npImgTmp = algImage.CAlgImage.create_np(terriInfo.OrganInfo[4], np.uint8)
        algImage.CAlgImage.set_clear(npImg, 0)

        # total image
        for inx, label in enumerate(listLabel) :
            anchorID = inx + 1
            territoryVertex = segmentProcess.get_query_vertex_with_seg_index(anchorID)
            algImage.CAlgImage.set_value(npImg, territoryVertex, anchorID)
        
        # second pass
        bSecondFlag = False
        algImage.CAlgImage.set_clear(npImgTmp, 0)
        for inx, label in enumerate(listLabel) :
            anchorID = inx + 1
            listBlobCoord = CCommandMultiTerritory.get_segment_vertex_from_np_value(npImg, anchorID, np.int32)
            # blob가 1개만 있는 경우에는 second pass를 진행할 필요 없음 
            if listBlobCoord is None :
                continue
            anchorCoord = dicAnchor[anchorID]
            for blobCoord in listBlobCoord :
                segSet = set(map(tuple, blobCoord))
                if any(tuple(pt) in segSet for pt in anchorCoord) == False : 
                    algImage.CAlgImage.set_value(npImgTmp, blobCoord, 255)
                    bSecondFlag = True
        
        if bSecondFlag == True :
            boundaryCoord = CCommandMultiTerritory.get_blob_boundary(npImgTmp, 255, np.int32)
            boundaryValue = algImage.CAlgImage.get_value(npImg, boundaryCoord)
            flag = boundaryValue > 0
            boundaryCoord = boundaryCoord[flag].reshape(-1, 3)
            boundaryValue = boundaryValue[flag]

            if len(boundaryCoord) != 0 and len(boundaryValue) != 0 : # sally(25.09.29)
                blobCoord = algImage.CAlgImage.get_vertex_from_np(npImgTmp, np.int32)

                segmentProcess = algSegment.CSegmentBasedVoxelProcess()
                for inx in range(0, boundaryCoord.shape[0]) :
                    segmentProcess.add_anchor(boundaryCoord[inx].reshape(-1, 3), boundaryValue[inx])
                segmentProcess.process(blobCoord)
                for inx in range(0, boundaryValue.shape[0]) :
                    anchorID = boundaryValue[inx]
                    territoryVertex = segmentProcess.get_query_vertex_with_seg_index(anchorID)
                    algImage.CAlgImage.set_value(npImg, territoryVertex, anchorID)

        origin = terriInfo.OrganInfo[1]
        spacing = terriInfo.OrganInfo[2]
        direction = terriInfo.OrganInfo[3]
        offset = algLinearMath.CScoMath.to_vec3([0.0, 0.0, 0.0])
        inputNiftiFullPath = os.path.join(fileAbsPath, "territory.nii.gz")

        ret = self.OptionInfo.find_recon_parameter_of_blendername(terriInfo.BlenderName)
        if ret is None :
            print("failed territory recon")
            return None
        # ret : (contour, gaussian, algorithm, resampling, listReconParam, triCnt)
        contour = ret[0]
        gaussian = ret[1]
        algorithm = ret[2]
        resampling = ret[3]
        listReconParam = ret[4]
        triCnt = ret[5]
        
        # label별 image 
        for inx, label in enumerate(listLabel) :
            anchorID = inx + 1
            coord = algImage.CAlgImage.get_vertex_from_np_value(npImg, anchorID, dtype=np.int32)
            if coord is None :
                continue

            algImage.CAlgImage.set_clear(npImgTmp, 0)
            algImage.CAlgImage.set_value(npImgTmp, coord, 255)
            algImage.CAlgImage.save_nifti_from_np(inputNiftiFullPath, npImgTmp, origin, spacing, direction, (2, 1, 0))
            polyData = reconstruction.CReconstruction.reconstruction_nifti(
                inputNiftiFullPath, 
                origin, spacing, direction, offset, 
                contour, gaussian, algorithm, resampling, listReconParam, triCnt,
                False
                )
            retListPolyData[inx] = polyData
        
        if os.path.exists(inputNiftiFullPath) == True :
            os.remove(inputNiftiFullPath)

        return retListPolyData

    
    @property
    def InputSkeleton(self) -> algSkeletonGraph.CSkeleton :
        return self.m_inputSkeleton
    @InputSkeleton.setter
    def InputSkeleton(self, skeleton : algSkeletonGraph.CSkeleton) :
        self.m_inputSkeleton = skeleton
    @property
    def InputTerriInfo(self) -> data.CTerritoryInfo :
        return self.m_inputTerriInfo
    @InputTerriInfo.setter
    def InputTerriInfo(self, inputTerriInfo : data.CTerritoryInfo) :
        self.m_inputTerriInfo = inputTerriInfo
    @property
    def InputCLMask(self) :
        return self.m_inputCLMask
    @InputCLMask.setter
    def InputCLMask(self, inputCLMask) :
        self.m_inputCLMask = inputCLMask


class CCommandMultiTerritoryLabel(CCommandMultiTerritory) :
    def __init__(self, mediator) :
        super().__init__(mediator)
        # input your code
        self.m_outputDataGroupPolyData = dataGroup.CDataGroupLabelingPolyData()
        self.m_dataGroupVertex = dataGroup.CDataGroupLabelingVertex()
    def clear(self) :
        # input your code
        self.m_outputDataGroupPolyData = None
        self.m_dataGroupVertex.clear()
        self.m_dataGroupVertex = None
        super().clear()
    def process(self) :
        super().process()

        if self.InputSkeleton is None :
            return
        if self.InputTerriInfo is None :
            return
        if self.InputCLMask is None : 
            return
        
        print("-- Start Do Territory --")

        self.m_dataGroupVertex.InputCLMask = self.InputCLMask
        self.m_dataGroupVertex.process(self.InputSkeleton)
        self.m_outputDataGroupPolyData.process(self.InputSkeleton)

        listLabel = self.m_dataGroupVertex.get_all_label()
        listVertex = []
        for inx, label in enumerate(listLabel) :
            vertex = self.m_dataGroupVertex.get_vertex(label)
            listVertex.append(vertex)

        retList = self._do_territory(listLabel, listVertex)
        if retList is None :
            print("failed territory")
            return
        
        for inx, label in enumerate(listLabel) :
            polyData = retList[inx]
            self.m_outputDataGroupPolyData.set_polydata(label, polyData)

        print("-- End Do Territory --")
    

    @property
    def OutputDataGroupPolyData(self) -> dataGroup.CDataGroupLabelingPolyData :
        return self.m_outputDataGroupPolyData


class CCommandMultiTerritoryKnife(CCommandMultiTerritory) :
    def __init__(self, mediator) :
        super().__init__(mediator)
        # input your code
        self.m_listCenterlineID = []
        self.m_inputKnifeCLID = -1
        self.m_inputKnifeIndex = -1

        self.m_outputWholeMesh = None
        self.m_outputSubMesh = None
    def clear(self) :
        # input your code
        self.m_inputKnifeCLID = -1
        self.m_inputKnifeIndex = -1
        self.m_listCenterlineID.clear()

        self.m_outputWholeMesh = None
        self.m_outputSubMesh = None
        super().clear()
    def process(self) :
        super().process()

        if self.InputSkeleton is None :
            return
        if self.InputTerriInfo is None :
            return
        if self.InputCLMask is None : 
            return

        wholeVertex, subVertex = self._make_whole_sub(self.m_listCenterlineID, self.InputKnifeCLID)

        if self.InputKnifeCLID >= 0 :
            # knifed clID 
            cl = self.InputSkeleton.get_centerline(self.InputKnifeCLID)
            iVertexCnt = cl.get_vertex_count()
            # wholeVertex
            for vertexInx in range(0, self.InputKnifeIndex) :
                if self.InputCLMask.get_flag(cl, vertexInx) == False :
                    continue

                vertex = cl.get_vertex(vertexInx)
                wholeVertex = np.concatenate((wholeVertex, vertex), axis=0)
            # subVertex
            for vertexInx in range(self.InputKnifeIndex, iVertexCnt) :
                if self.InputCLMask.get_flag(cl, vertexInx) == False :
                    continue

                vertex = cl.get_vertex(vertexInx)
                if subVertex is None :
                    subVertex = vertex.copy()
                else :
                    subVertex = np.concatenate((subVertex, vertex), axis=0)
        
        if subVertex is None :
            print("invalid territory")
            return
        
        listLabel = ["whole", "sub"]
        listVertex = [wholeVertex, subVertex]
        retList = self._do_territory(listLabel, listVertex)
        if retList is None :
            print("failed territory")
            return
        
        self.m_outputWholeMesh = retList[0]
        self.m_outputSubMesh = retList[1]
    
    def add_cl_id(self, id : int) :
        self.m_listCenterlineID.append(id)
    def clear_cl_id(self) :
        self.m_listCenterlineID.clear()


    # protected 
    def _make_whole_sub(self, listCLID : list, exceptCLID = -1) :
        wholeVertex = []
        subVertex = []
        
        iCLCnt = self.InputSkeleton.get_centerline_count()
        for inx in range(0, iCLCnt) :
            cl = self.InputSkeleton.get_centerline(inx)
            if cl.ID == exceptCLID :
                continue

            iVertexCnt = cl.get_vertex_count()
            if cl.ID in listCLID :
                for vertexInx in range(0, iVertexCnt) :
                    vertex = cl.get_vertex(vertexInx)
                    if self.InputCLMask.get_flag(cl, vertexInx) == True :
                        vertex = vertex.reshape(-1)
                        subVertex.append(vertex)
            else :
                for vertexInx in range(0, iVertexCnt) :
                    vertex = cl.get_vertex(vertexInx)
                    if self.InputCLMask.get_flag(cl, vertexInx) == True :
                        vertex = vertex.reshape(-1)
                        wholeVertex.append(vertex)
        wholeVertex = np.array(wholeVertex)
        if len(subVertex) > 0 :
            subVertex = np.array(subVertex)
        else :
            subVertex = None
        return (wholeVertex, subVertex)     


    @property
    def InputKnifeCLID(self) -> int :
        return self.m_inputKnifeCLID
    @InputKnifeCLID.setter
    def InputKnifeCLID(self, inputKnifeCLID : int) :
        self.m_inputKnifeCLID = inputKnifeCLID
    @property
    def InputKnifeIndex(self) -> int :
        return self.m_inputKnifeIndex
    @InputKnifeIndex.setter
    def InputKnifeIndex(self, inputKnifeIndex : int) :
        self.m_inputKnifeIndex = inputKnifeIndex
    
    @property
    def OutputWholeMesh(self) -> vtk.vtkPolyData :
        return self.m_outputWholeMesh
    @property
    def OutputSubMesh(self) -> vtk.vtkPolyData :
        return self.m_outputSubMesh



if __name__ == '__main__' :
    pass


# print ("ok ..")

