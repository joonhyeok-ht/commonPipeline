import sys
import os
import numpy as np
import shutil
import vtk
import subprocess

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

import data as data

import userData as userData

import command.commandRecon as commandRecon
import commandReconKidneyBatch as commandReconKidneyBatch


class CUserDataKB(userData.CUserData) :
    s_userDataKey = "KidneyBatch"


    def __init__(self, data : data.CData, mediator) :
        super().__init__(data, CUserDataKB.s_userDataKey)
        # input your code
        self.m_mediator = mediator
    def clear(self) :
        # input your code
        self.m_mediator = None
        super().clear()

    def load_patient(self) -> bool :
        if super().load_patient() == False :
            return False
        # input your code
        
        return True
    

    # override
    def override_recon(self) :
        optioninfoPath = self.Data.OptionInfoPath
        resPath = os.path.join(optioninfoPath, "Res")
        scriptPath = os.path.join(resPath, "kidney_batch")
        scriptFullPath = os.path.join(scriptPath, f"blenderScriptRecon.py")

        patientID = self.Data.PatientID
        saveName = f"{patientID}_recon"
        blenderFullPath = os.path.join(self.Data.OutputPatientPath, f"{saveName}.blend")

        cmd = commandReconKidneyBatch.CCommandReconDevelopKidneyBatch(self.m_mediator)
        cmd.InputData = self.Data
        cmd.InputBlenderScritpFullPath = scriptFullPath
        cmd.PatientBlenderFullPath = blenderFullPath
        cmd.process()
    def override_clean(self) :
        optioninfoPath = self.Data.OptionInfoPath
        resPath = os.path.join(optioninfoPath, "Res")
        scriptPath = os.path.join(resPath, "common")
        scriptFullPath = os.path.join(scriptPath, f"blenderScriptClean.py")

        # patientID = self.Data.PatientID
        # outputPatientPath = self.Data.OutputPatientPath

        # saveBlenderFullPath = os.path.join(outputPatientPath, f"{patientID}.blend")
        # srcBlenderFullPath = os.path.join(outputPatientPath, f"{patientID}_recon.blend")

        # if os.path.exists(srcBlenderFullPath) == False :
        #     print("not found recon blender file")
        #     return

        # # 기존것은 지움
        # if os.path.exists(saveBlenderFullPath) == True :
        #     os.remove(saveBlenderFullPath)
        # # 새롭게 생성 
        # shutil.copy(srcBlenderFullPath, saveBlenderFullPath)

        # cmd = commandRecon.CCommandReconDevelopClean(self.m_mediator)
        # cmd.InputData = self.Data
        # cmd.InputBlenderScritpFullPath = scriptFullPath
        # cmd.process()


    @property
    def Data(self) -> data.CData :
        return self.m_data




    

if __name__ == '__main__' :
    pass


# print ("ok ..")

