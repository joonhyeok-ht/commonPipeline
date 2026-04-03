# -*- coding: utf-8 -*-
'''
File : sepKidneyTumor.py
Version : 2026_03_23
'''
import os
import sys
import numpy as np

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileCommonPath = os.path.dirname(fileAbsPath)
fileStateProjectPath = os.path.dirname(fileCommonPath)
fileStatePath = os.path.dirname(fileStateProjectPath)
fileAppPath = os.path.dirname(fileStatePath)
fileToolPath = os.path.dirname(fileAppPath)
fileCommonPipelinePath = os.path.dirname(fileToolPath)

sys.path.append(fileAbsPath)
sys.path.append(fileCommonPath)
sys.path.append(fileStateProjectPath)
sys.path.append(fileStatePath)
sys.path.append(fileAppPath)
sys.path.append(fileToolPath)
sys.path.append(fileCommonPipelinePath)

import Algorithm.scoUtil as scoUtil
import Algorithm.scoBuffer as scoBuffer


class CSepKidneyTumor() :
    eMaskID_kidney = 100
    eMaskID_tumor = 1

    eSurfaceType_outside = 0
    eSurfaceType_inside = 1
    eSurfaceType_ambiguous = 2

    @staticmethod
    def create_mask(refPath : str, type : str, clearValue, voxel) -> scoBuffer.CScoBuffer3D :
        sitkImg = scoUtil.CScoUtilSimpleITK.load_image(refPath, None)
        npImg = scoUtil.CScoUtilSimpleITK.sitkImg_to_npImg(sitkImg, type).transpose((2, 1, 0))
        mask = scoBuffer.CScoBuffer3D(npImg.shape, type)
        mask.all_set_voxel(clearValue)

        xInx, yInx, zInx = np.where(npImg > 0)
        mask.set_voxel((xInx, yInx, zInx), voxel)
        return mask
    @staticmethod
    def load_mask(fullPath : str, mask : scoBuffer.CScoBuffer3D, type : str, voxel) :
        sitkImg = scoUtil.CScoUtilSimpleITK.load_image(fullPath, None)
        npImg = scoUtil.CScoUtilSimpleITK.sitkImg_to_npImg(sitkImg, type).transpose((2, 1, 0))
        xInx, yInx, zInx = np.where(npImg > 0)
        mask.set_voxel((xInx, yInx, zInx), voxel)
    @staticmethod
    def append_mask(dstMask : scoBuffer.CScoBuffer3D, srcMask : scoBuffer.CScoBuffer3D, voxel) :
        xInx, yInx, zInx = srcMask.get_voxel_inx_with_greater(0)
        dstMask.set_voxel((xInx, yInx, zInx), voxel)


    def __init__(self) -> None :
        super().__init__()
        self.m_inputKidneyPath = ""
        self.m_listTumorPath = []
        self.m_outputKidneyPath = ""
    def clear(self) :
        self.m_inputKidneyPath = ""
        self.m_outputKidneyPath = ""
        self.clear_tumor_path()
    def process(self) :
        if self.InputKidneyPath == "" :
            print(f"SepKidneyTumor.process() : not setting kidney path")
            return 
        if self.get_tumor_path_count() == 0 :
            print(f"SepKidneyTumor.process() : TumorPhase is None. ")
            return
        if os.path.exists(self.InputKidneyPath) == False :
            print(f"SepKidneyTumor.process() : not found kidney file")
            return
        os.makedirs(os.path.dirname(self.OutputKidneyPath), exist_ok=True)
         
        self.m_maskKidney = CSepKidneyTumor.create_mask(self.InputKidneyPath, "uint8", 0, CSepKidneyTumor.eMaskID_kidney)

        self.m_maskTumor = self.m_maskKidney.clone("uint8")
        self.m_maskTumor.all_set_voxel(0)
        for inx in range(0, self.get_tumor_path_count()) : 
            exoPath = self.get_tumor_path(inx) 
            
            if os.path.exists(exoPath) == False :
                print(f"SepKidneyTumor.process() : skipped tumor {exoPath}")
                continue

            exoMask = CSepKidneyTumor.create_mask(exoPath, "uint8", 0, self.eMaskID_tumor)
            CSepKidneyTumor.append_mask(self.m_maskTumor, exoMask, self.eMaskID_tumor)
        CSepKidneyTumor.append_mask(self.m_maskKidney, self.m_maskTumor, self.eMaskID_tumor)

        self._erode()
        self._save_nifti()


    
    def add_tumor_path(self, tumorPath : str) :
        self.m_listTumorPath.append(tumorPath)
    def get_tumor_path_count(self) -> int :
        return len(self.m_listTumorPath)
    def get_tumor_path(self, inx : int) -> str :
        return self.m_listTumorPath[inx]
    def clear_tumor_path(self) :
        self.m_listTumorPath.clear()
    
    
    @property
    def InputKidneyPath(self) -> str :
        return self.m_inputKidneyPath
    @InputKidneyPath.setter
    def InputKidneyPath(self, inputKidneyPath : str) :
        self.m_inputKidneyPath = inputKidneyPath
    @property
    def OutputKidneyPath(self) -> str :
        return self.m_outputKidneyPath
    @OutputKidneyPath.setter
    def OutputKidneyPath(self, outputKidneyPath : str) :
        self.m_outputKidneyPath = outputKidneyPath
    
    
    # protected
    def _is_tumor_surface(self, mask : scoBuffer.CScoBuffer3D, voxelInx : tuple) :
        ret = int(np.sum(mask.m_npBuf[voxelInx[0] - 1 : voxelInx[0] + 2, voxelInx[1] - 1 : voxelInx[1] + 2, voxelInx[2] - 1 : voxelInx[2] + 2]))
        if ret < 27 :
            return True
        return False
    def _get_surface_voxel(self, mask : scoBuffer.CScoBuffer3D) :
        xInx, yInx, zInx = mask.get_voxel_inx_with_greater(0)

        surfaceXInx = []
        surfaceYInx = []
        surfaceZInx = []

        for inx, _ in enumerate(xInx) :
            voxelInx = (xInx[inx], yInx[inx], zInx[inx])
            if self._is_tumor_surface(mask, voxelInx) == True :
                surfaceXInx.append(voxelInx[0])
                surfaceYInx.append(voxelInx[1])
                surfaceZInx.append(voxelInx[2])
        
        return (surfaceXInx, surfaceYInx, surfaceZInx)
    def _get_surface_type(self, mask : scoBuffer.CScoBuffer3D, voxelInx : tuple) :
        """
        ret
            0 : outside surface
            1 : inside surface
            2 : ambiguous surface
        """
        list0 = []
        list1 = []
        list100 = []
        for z in range(voxelInx[2] - 1, voxelInx[2] + 2) :
            for y in range(voxelInx[1] - 1, voxelInx[1] + 2) :
                for x in range(voxelInx[0] - 1, voxelInx[0] + 2) :
                    voxel = mask.get_voxel((x, y, z))
                    if voxel == 0 :
                        list0.append(0)
                    elif voxel == 1 :
                        list1.append(1)
                    else :
                        list100.append(100)

        len0 = len(list0)
        len100 = len(list100)
        if len0 > 0 and len100 > 0 :
            return self.eSurfaceType_ambiguous
        elif len0 > 0 :
            return self.eSurfaceType_outside
        else :
            return self.eSurfaceType_inside
    def _erode(self) :
        clearXInx = []
        clearYInx = []
        clearZInx = []
        kidneyXInx = []
        kidneyYInx = []
        kidneyZInx = []

        iCnt = 0
        inx = 0
        bFlag = False
        surfaceXInx, surfaceYInx, surfaceZInx = self._get_surface_voxel(self.m_maskTumor)

        while len(surfaceXInx) > 0 :
            clearXInx.clear()
            clearYInx.clear()
            clearZInx.clear()
            kidneyXInx.clear()
            kidneyYInx.clear()
            kidneyZInx.clear()
            for inx in range(0, len(surfaceXInx)) :
                voxelInx = (surfaceXInx[inx], surfaceYInx[inx], surfaceZInx[inx])
                surfaceType = self._get_surface_type(self.m_maskKidney, voxelInx)

                if surfaceType == self.eSurfaceType_inside :
                    kidneyXInx.append(voxelInx[0])
                    kidneyYInx.append(voxelInx[1])
                    kidneyZInx.append(voxelInx[2])
                elif surfaceType == self.eSurfaceType_ambiguous :
                    if bFlag == False :
                        clearXInx.append(voxelInx[0])
                        clearYInx.append(voxelInx[1])
                        clearZInx.append(voxelInx[2])
                    else :
                        kidneyXInx.append(voxelInx[0])
                        kidneyYInx.append(voxelInx[1])
                        kidneyZInx.append(voxelInx[2])
                else :
                    clearXInx.append(voxelInx[0])
                    clearYInx.append(voxelInx[1])
                    clearZInx.append(voxelInx[2])

            self.m_maskKidney.set_voxel((clearXInx, clearYInx, clearZInx), 0)
            self.m_maskKidney.set_voxel((kidneyXInx, kidneyYInx, kidneyZInx), self.eMaskID_kidney)
            self.m_maskTumor.set_voxel((surfaceXInx, surfaceYInx, surfaceZInx), 0)

            print(f"passed erode : {iCnt}")

            inx += 1
            iCnt += 1
            if bFlag == False :
                bFlag = True
            else :
                bFlag = False
            surfaceXInx, surfaceYInx, surfaceZInx = self._get_surface_voxel(self.m_maskTumor)
    def _save_nifti(self) :
        refPath = self.InputKidneyPath
        sitkImg = scoUtil.CScoUtilSimpleITK.load_image(refPath, None)
        origin = sitkImg.GetOrigin()
        direction = sitkImg.GetDirection()
        spacing = sitkImg.GetSpacing()
        
        sepTumorKidneyMask = self.m_maskKidney

        maskBuf = scoBuffer.CScoBuffer3D(sepTumorKidneyMask.Shape, "uint8")
        maskBuf.all_set_voxel(0)
        xVoxel, yVoxel, zVoxel = sepTumorKidneyMask.get_voxel_inx_with_greater(0)
        maskBuf.set_voxel((xVoxel, yVoxel, zVoxel), 255)
        sitkImg = maskBuf.get_sitk_img(origin, spacing, direction, (2, 1, 0))
        
        scoUtil.CScoUtilSimpleITK.save_nifti(self.OutputKidneyPath, sitkImg)

        print(f"save : {self.OutputKidneyPath}")


if __name__ == '__main__' :
    pass



