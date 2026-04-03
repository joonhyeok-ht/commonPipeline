import sys
import os
import numpy as np
import shutil
import glob
import vtk
import subprocess
import copy
import SimpleITK as sitk
import math
from collections import Counter

from PySide6.QtCore import Qt, QItemSelection, QItemSelectionModel
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QTreeView, QPushButton, QLineEdit, QLabel, QSizePolicy, QListWidget, QFileDialog, QFrame, QCheckBox, QTabWidget, QComboBox, QListWidgetItem, QMessageBox, QAbstractItemView
from PySide6.QtGui import QStandardItemModel, QStandardItem
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileStateProjectPath = os.path.dirname(fileAbsPath)
fileStatePath = os.path.dirname(fileStateProjectPath)
fileAppPath = os.path.dirname(fileStatePath)
fileToolPath = os.path.dirname(fileAppPath)
fileCommonPipelinePath = os.path.dirname(fileToolPath)

sys.path.append(fileAbsPath)
sys.path.append(fileStateProjectPath)
sys.path.append(fileStatePath)
sys.path.append(fileAppPath)
sys.path.append(fileToolPath)
sys.path.append(fileCommonPipelinePath)


import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algImage as algImage
import AlgUtil.algVTK as algVTK

import Block.optionInfo as optionInfo
import Block.niftiContainer as niftiContainer
import Block.originOffset as originOffset
import Block.removeStricture as removeStricture
import Block.registration as registration
import Block.resampling as resamplingB
import Block.reconstruction as reconstruction
import Block.meshHealing as meshHealing
import Block.meshBoolean as meshBoolean
import Block.meshDecimation as meshDecimation

import vtkObjInterface as vtkObjInterface

import data as data

import userData as userData

import command.commandRecon as commandRecon

import kbBlock.createDiaphragm as createDiaphragm
import kbBlock.sepKidneyTumor as kbSepKidney



class CCommandReconDevelopKidneyBatch(commandRecon.CCommandRecon) :
    '''
    Desc : common pipeline reconstruction step에서 Recon 수행
    '''
    def __init__(self, mediator) :
        super().__init__(mediator)
        # input your code
        self.m_anchorKidneyName = ""
        self.m_outputKidneyName = ""
        self.m_listExoName = []
    def clear(self) :
        # input your code
        self.m_anchorKidneyName = ""
        self.m_outputKidneyName = ""
        self.m_listExoName.clear()
        super().clear()
    def process(self) :
        super().process()

        if self.AnchorKidneyName == "" :
            print("recon error : not setting anchor kidney")
            return
        if self.OutputKidneyName == "" :
            print("recon error : not setting output kidney")
            return
        if len(self.m_listExoName) == 0 :
            print("recon error : not setting tumor or cyst exo")
            return

        # input your code
        phase = None
        phaseInfoFullPath = self.PhaseInfoFullPath
        if os.path.exists(phaseInfoFullPath) == True :
            fileLoadPhaseInfoBlock = niftiContainer.CFileLoadPhaseInfo()
            fileLoadPhaseInfoBlock.InputPath = self.InputData.OutputPatientPath
            fileLoadPhaseInfoBlock.InputFileName = commandRecon.CCommandReconInterface.s_phaseInfoFileName
            phase = fileLoadPhaseInfoBlock.process()
        else :
            phase = self._create_phase()
            originOffsetBlock = originOffset.COriginOffset()
            originOffsetBlock.InputOptionInfo = self.InputData.OptionInfo
            originOffsetBlock.InputPhase = phase
            originOffsetBlock.process()

            registrationBlock = registration.CRegistration()
            registrationBlock.InputOptionInfo = self.InputData.OptionInfo
            registrationBlock.InputMaskPath = self.InputMaskPath
            registrationBlock.process()

            self._update_phase_offset(self.InputData.OptionInfo, registrationBlock, originOffsetBlock, phase)
            fileSavePhaseInfoBlock = niftiContainer.CFileSavePhaseInfo()
            fileSavePhaseInfoBlock.InputPhase = phase
            fileSavePhaseInfoBlock.OutputSavePath = self.InputData.OutputPatientPath
            fileSavePhaseInfoBlock.OutputFileName = commandRecon.CCommandReconInterface.s_phaseInfoFileName
            fileSavePhaseInfoBlock.process()
        
        diaphragm = createDiaphragm.CCreateDiaphragm()
        diaphragm.InputPath = self.InputMaskPath
        diaphragm.OutputPath = self.InputMaskPath
        diaphragm.InputNiftiName = "Skin.nii.gz"
        diaphragm.process()

        '''
        desc 
            registration info를 이용하여 
            서로 다른 phase에 있는 Tumor_exo와 Cyst_exo 의 경우 
            Cyst_exo의 phase를 tumor의 phase로 변환하여 새로운 cyst mask파일을 생성함

        - tumorPhase 얻어와야 함 
        - 기존 niftiContinerBlock 제거 

        - 결론 CResamplingToPhase 하라는 얘기임 

        - cyst phase도 option에서 resampling 영역에 미리 추가할 수 있음 
                ["Cyst_exo", "Cyst_exo", "DP", -1],
                ["Cyst_endo", "Cyst_endo", "DP", -1],
                ["Tumor_exo", "Tumor_exo", "DP", -1],
                ["Tumor_endo", "Tumor_endo", "DP", -1]
        '''

        resamplingToPhaseBlock = resamplingB.CResamplingToPhase()
        resamplingToPhaseBlock.InputOptionInfo = self.InputData.OptionInfo
        resamplingToPhaseBlock.InputMaskPath = self.InputMaskPath
        resamplingToPhaseBlock.InputPhase = phase
        resamplingToPhaseBlock.OutputMaskPath = self.InputMaskPath
        resamplingToPhaseBlock.process()

        resamplingToMinSpacingBlock = resamplingB.CResamplingToMinSpacing()
        resamplingToMinSpacingBlock.InputMaskPath = self.InputMaskPath
        resamplingToMinSpacingBlock.InputOptionInfo = self.InputData.OptionInfo
        resamplingToMinSpacingBlock.OutputMaskPath = self.InputMaskPath
        resamplingToMinSpacingBlock.process()


        inputFullPath = os.path.join(self.InputMaskPath, f"{self.AnchorKidneyName}.nii.gz")
        outputFullPath = os.path.join(self.InputMaskPath, f"{self.OutputKidneyName}.nii.gz")
        sepKidneyTumorBlock = kbSepKidney.CSepKidneyTumor()
        sepKidneyTumorBlock.InputKidneyPath = inputFullPath
        sepKidneyTumorBlock.OutputKidneyPath = outputFullPath
        for exoName in self.m_listExoName :
            exoFullPath = os.path.join(self.InputMaskPath, f"{exoName}.nii.gz")
            sepKidneyTumorBlock.add_tumor_path(exoFullPath)
        sepKidneyTumorBlock.process()
        

        removeStrictureBlock = removeStricture.CRemoveStricture()
        removeStrictureBlock.InputOptionInfo = self.OptionInfo
        removeStrictureBlock.InputMaskPath = self.InputMaskPath
        removeStrictureBlock.OutputMaskPath = self.InputMaskPath
        removeStrictureBlock.process()

        reconstructionBlock = reconstruction.CReconstruction()
        reconstructionBlock.InputOptionInfo = self.InputData.OptionInfo
        reconstructionBlock.InputMaskPath = self.InputMaskPath
        reconstructionBlock.InputPhase = phase
        reconstructionBlock.OutputPath = self.OutputPath
        reconstructionBlock.process()

        meshHealingBlock = meshHealing.CMeshHealing()
        meshHealingBlock.InputPath = self.OutputPath
        meshHealingBlock.InputOptionInfo = self.InputData.OptionInfo
        meshHealingBlock.process()

        meshBooleanBlock = meshBoolean.CMeshBoolean()
        meshBooleanBlock.InputPath = self.OutputPath
        meshBooleanBlock.InputOptionInfo = self.InputData.OptionInfo
        meshBooleanBlock.process()

        meshDecimationBlok = meshDecimation.CMeshDecimation()
        meshDecimationBlok.InputPath = self.OutputPath
        meshDecimationBlok.InputOptionInfo = self.InputData.OptionInfo
        meshDecimationBlok.process()

        diaphragm.clear()
        removeStrictureBlock.clear()
        reconstructionBlock.clear()
        meshHealingBlock.clear()
        meshBooleanBlock.clear()
        meshDecimationBlok.clear()
    def process_resampling(self) :
        originMaskPath = self.MaskPath
        if os.path.exists(originMaskPath) == False :
            print(f"colon recon : not found mask path - {originMaskPath}")
            return

        copiedMaskPath = self.CopiedMaskPath
        if os.path.exists(copiedMaskPath) == False :
            os.makedirs(copiedMaskPath, exist_ok=True)
            # nii.gz 파일 복사
            for file in glob.glob(os.path.join(originMaskPath, "*.nii.gz")):
                shutil.copy(file, copiedMaskPath)
        
        phase = None

        phaseInfoFullPath = self.PhaseInfoFullPath
        if os.path.exists(phaseInfoFullPath) == True :
            fileLoadPhaseInfoBlock = niftiContainer.CFileLoadPhaseInfo()
            fileLoadPhaseInfoBlock.InputPath = self.InputData.OutputPatientPath
            fileLoadPhaseInfoBlock.InputFileName = commandRecon.CCommandReconInterface.s_phaseInfoFileName
            phase = fileLoadPhaseInfoBlock.process()
        else :
            phase = self._create_phase()
            originOffsetBlock = originOffset.COriginOffset()
            originOffsetBlock.InputOptionInfo = self.InputData.OptionInfo
            originOffsetBlock.InputPhase = phase
            originOffsetBlock.process()

            registrationBlock = registration.CRegistration()
            registrationBlock.InputOptionInfo = self.InputData.OptionInfo
            registrationBlock.InputMaskPath = self.CopiedMaskPath
            registrationBlock.process()

            self._update_phase_offset(self.InputData.OptionInfo, registrationBlock, originOffsetBlock, phase)
            fileSavePhaseInfoBlock = niftiContainer.CFileSavePhaseInfo()
            fileSavePhaseInfoBlock.InputPhase = phase
            fileSavePhaseInfoBlock.OutputSavePath = self.InputData.OutputPatientPath
            fileSavePhaseInfoBlock.OutputFileName = commandRecon.CCommandReconInterface.s_phaseInfoFileName
            fileSavePhaseInfoBlock.process()

        resamplingToPhaseBlock = resamplingB.CResamplingToPhase()
        resamplingToPhaseBlock.InputOptionInfo = self.InputData.OptionInfo
        resamplingToPhaseBlock.InputMaskPath = self.CopiedMaskPath
        resamplingToPhaseBlock.InputPhase = phase
        resamplingToPhaseBlock.OutputMaskPath = self.CopiedMaskPath
        resamplingToPhaseBlock.process()

        resamplingToMinSpacingBlock = resamplingB.CResamplingToMinSpacing()
        resamplingToMinSpacingBlock.InputMaskPath = self.CopiedMaskPath
        resamplingToMinSpacingBlock.InputOptionInfo = self.InputData.OptionInfo
        resamplingToMinSpacingBlock.OutputMaskPath = self.CopiedMaskPath
        resamplingToMinSpacingBlock.process()


    def add_exo_name(self, exoPath : str) :
        self.m_listExoName.append(exoPath)
    def get_exo_name_count(self) -> int :
        return len(self.m_listExoName)
    def get_exo_name(self, inx : int) -> str :
        return self.m_listExoName[inx]
    def clear_name_path(self) :
        self.m_listExoName.clear()
    # protected


    @property
    def AnchorKidneyName(self) -> str :
        return self.m_anchorKidneyName
    @AnchorKidneyName.setter
    def AnchorKidneyName(self, anchorKidneyName : str) :
        self.m_anchorKidneyName = anchorKidneyName
    @property
    def OutputKidneyName(self) -> str :
        return self.m_outputKidneyName
    @OutputKidneyName.setter
    def OutputKidneyName(self, outputKidneyName : str) :
        self.m_outputKidneyName = outputKidneyName



    
    

if __name__ == '__main__' :
    pass


# print ("ok ..")

