'''
File : makeInputFolder.py
Version : 2025_03_27
'''
# 24.11.01 : add Lung
# 25.03.27 : 25'3월 기준으로 output 폴더구조 변경, nifti파일만 따로 zip으로 묶는기능 추가

import os
import shutil
import sys
from distutils.dir_util import copy_tree
import glob
from pathlib import Path


class CMakeInputFolder :
    TAG = "[MakeInputFolder] "
    s_dataRootName = "dataRoot"

    s_dicomName = "01_DICOM"
    s_saveName = "02_SAVE"

    s_maskName = "01_MASK"
    s_blenderSaveName = "02_BLENDER_SAVE"
    s_pneumoSaveName = "03_PNEUMO_SAVE"

    sZip_Dicom = "DICOM.zip"


    def __init__(self) -> None :
        self.m_zipPath = ""

        self.m_patientID = "" 
        self.m_dataRootPath = "" 
        self.m_dataRootPatientPath = "" 

        self.m_dicomPath = ""
        self.m_savePath = ""

        self.m_maskPath = ""
        self.m_blenderSavePath = ""
        self.m_pneumoSavePath = ""

        self.m_listPhaseZip = []
        self.m_listPhaseZipName = []

        self.m_bReady = False
    def clear(self) :
        self.m_zipPath = ""

        self.m_patientID = ""
        self.m_dataRootPath = ""
        self.m_dataRootPatientPath = ""

        self.m_dicomPath = ""
        self.m_savePath = ""

        self.m_maskPath = ""
        self.m_blenderSavePath = ""
        self.m_pneumoSavePath = ""

        self.m_listPhaseZip.clear()
        self.m_listPhaseZipName.clear()

        self.m_bReady = False
    def process(self) -> bool :
        self.Ready = False

        if self.m_zipPath == "" :
            print(self.TAG, "ERROR - please setting zip full path")
            return False
        
        self.m_patientID = os.path.basename(self.m_zipPath)
        self.m_dataRootPath = os.path.join(self.m_zipPath, CMakeInputFolder.s_dataRootName)
        self.m_dataRootPatientPath = os.path.join(self.m_dataRootPath, self.m_patientID)

        self.m_dicomPath = os.path.join(self.m_dataRootPatientPath, CMakeInputFolder.s_dicomName)
        self.m_savePath = os.path.join(self.m_dataRootPatientPath, CMakeInputFolder.s_saveName)

        self.m_maskPath = os.path.join(self.m_savePath, CMakeInputFolder.s_maskName)
        self.m_blenderSavePath = os.path.join(self.m_savePath, CMakeInputFolder.s_blenderSaveName)
        self.m_pneumoSavePath = os.path.join(self.m_savePath, CMakeInputFolder.s_pneumoSaveName)

        if os.path.exists(self.m_dicomPath) == False :
            os.makedirs(self.m_dicomPath)
        if os.path.exists(self.m_maskPath) == False :
            os.makedirs(self.m_maskPath)
        if os.path.exists(self.m_blenderSavePath) == False :
            os.makedirs(self.m_blenderSavePath)
        if os.path.exists(self.m_pneumoSavePath) == False :
            os.makedirs(self.m_pneumoSavePath)

        # dicom unzip
        dicomFullPath = os.path.join(self.m_zipPath, self.sZip_Dicom)
        if os.path.exists(dicomFullPath) :
            shutil.unpack_archive(dicomFullPath, self.m_dicomPath, "zip")

        files = os.listdir(self.m_zipPath)
        self.m_listPhaseZip = [file for file in files if file.endswith(".zip")]
        if len(self.m_listPhaseZip) == 0 :
            print(self.TAG, "ERROR - not found zip files.")
            return False
        
        self.m_listPhaseZipName = [zipFile.split('.')[0] for zipFile in self.m_listPhaseZip]

        # create mask phase folder & unzip 
        for phase in self.m_listPhaseZipName :
            phaseZipPath = os.path.join(self.m_zipPath, f"{phase}.zip")
            shutil.unpack_archive(phaseZipPath, self.m_maskPath, "zip")
            
        # make mask zip 
        zipName = os.path.join(self.m_dataRootPath, f"{self.m_patientID}_mask_miop")
        shutil.make_archive(zipName, 'zip', self.m_maskPath)

        self.Ready = True
        return True
    
    def copy_mask(self, copiedMaskPath : str) :
        # mask copy 
        if os.path.exists(copiedMaskPath) == False :
            os.makedirs(copiedMaskPath, exist_ok=True)

        phaseList = self.m_listPhaseZipName
        for phase in phaseList :
            if phase == "" :
                continue

            originMaskPhasePath = os.path.join(self.m_maskPath, phase)
            if os.path.exists(originMaskPhasePath) == False :
                continue

            for file in glob.glob(os.path.join(originMaskPhasePath, "*.nii.gz")):
                shutil.copy(file, copiedMaskPath)
    def copy_target_mask(self, targetMaskFolder : str, individualPhase : str, copiedMaskPath : str) :
        if os.path.exists(copiedMaskPath) == False :
            os.makedirs(copiedMaskPath, exist_ok=True)
        
        inputFolder = Path(targetMaskFolder)
        maskList = [
            f.name
            for f in inputFolder.iterdir()
            if f.is_file() and f.name.lower().endswith(".nii.gz")
        ]
        # maskNameList = [maskFile.split(".")[0] for maskFile in maskList]

        # 해당 mask file이 기존 phase 폴더에 있다면 지운다. 
        phaseList = self.m_listPhaseZipName
        for phase in phaseList :
            if phase == "" :
                continue

            originMaskPhasePath = os.path.join(self.m_maskPath, phase)
            if os.path.exists(originMaskPhasePath) == False :
                continue

            for maskFile in maskList :
                checkOriginMaskFullPath = os.path.join(originMaskPhasePath, maskFile)
                if os.path.exists(checkOriginMaskFullPath) == True :
                    os.remove(checkOriginMaskFullPath)
            
        # 해당 mask folder를 originMaskPhasePath로 복사
        originMaskPhasePath = os.path.join(self.m_maskPath, individualPhase)
        if os.path.exists(originMaskPhasePath) == False :
            os.makedirs(originMaskPhasePath, exist_ok=True)
        # 해당 mask folder를 copiedMaskPath와 dataRoot Mask Path로 복사 
        for maskFile in maskList :
            maskFullPath = os.path.join(targetMaskFolder, maskFile)
            shutil.copy(maskFullPath, copiedMaskPath)
            shutil.copy(maskFullPath, originMaskPhasePath)

        # make mask zip 
        zipName = os.path.join(self.m_dataRootPath, f"{self.m_patientID}_mask_miop")
        shutil.make_archive(zipName, 'zip', self.m_maskPath)

        # refresh origin zip 
        listFolderName = [folderName for folderName in os.listdir(self.m_maskPath) if os.path.isdir(os.path.join(self.m_maskPath, folderName))]
        for folderName in listFolderName :
            if folderName not in self.m_listPhaseZipName : 
                continue
            zipName = os.path.join(self.m_zipPath, f"{folderName}")
            folderPath = os.path.join(self.m_maskPath, folderName)
            shutil.make_archive(zipName, 'zip', folderPath)

    

    @property
    def Ready(self) -> bool :
        return self.m_bReady
    @Ready.setter
    def Ready(self, bReady : bool) :
        self.m_bReady = bReady
    @property
    def ZipPath(self) :
        return self.m_zipPath
    @ZipPath.setter
    def ZipPath(self, zipPath : str) :
        self.m_zipPath = zipPath
    @property
    def PatientID(self) -> str :
        return self.m_patientID
    @property
    def DataRootPath(self) -> str :
        return self.m_dataRootPath
    @property
    def MaskPath(self) -> str :
        return self.m_maskPath
    @property
    def BlenderSavePath(self) -> str :
        return self.m_blenderSavePath


if __name__ == "__main__" :
    pass
    # test = CMakeInputFolder()
    # test.ZipPath = "D:\\jys\\StomachKidney_newfolder\\zippath" #01014urk_4input"
    # test.FolderMode = test.eMode_Kidney #test.eMode_Kidney  #test.eMode_Stomach
    # test.process()

    

    