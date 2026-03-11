import sys
import os
import numpy as np
import shutil
import vtk
import subprocess
from pathlib import Path

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileStatePath = os.path.dirname(fileAbsPath)
fileAppPath = os.path.dirname(fileStatePath)
fileToolPath = os.path.dirname(fileAppPath)
fileCommonPipelinePath = os.path.dirname(fileToolPath)

sys.path.append(fileAbsPath)
sys.path.append(fileStatePath)
sys.path.append(fileAppPath)
sys.path.append(fileToolPath)
sys.path.append(fileCommonPipelinePath)


import data as data


class CUserData :
    @staticmethod
    def blender_process_load(blenderExe : str, blenderFullPath : str) :
        cmd = f"{blenderExe} {blenderFullPath}"
        os.system(cmd)
    @staticmethod
    def blender_process(blenderExe : str, scriptFullPath : str, optionFullPath : str, inputPath : str, outputPath : str, saveName : str, bBackground : bool = False) :
        '''
        Desc
            - blender script를 통해 stl 파일들을 import 하여 새로운 blend 파일을 생성한다.
        Input 
            - blenderExe : option.json의 "BlenderExe" value
            - scriptFullPath : blender가 실행해야 할 scirpt fullpath
            - optionFullPath : option.json의 fullpath
            - inputPath : import할 stl 파일들이 저장 된 folder path
            - outputPath : blend 파일이 저장 될 path
            - saveName : 저장 될 blend 파일명
            - bBackground : blender를 background로 실행 시킬 여부 지정 
        '''
        saveName = f"{saveName}.blend"
        if bBackground == False :
            cmd = f"{blenderExe} --python {scriptFullPath} -- --optionFullPath {optionFullPath} --inputPath {inputPath} --outputPath {outputPath} --saveName {saveName}"
        else :
            cmd = f"{blenderExe} -b --python {scriptFullPath} -- --optionFullPath {optionFullPath} --inputPath {inputPath} --outputPath {outputPath} --saveName {saveName}"
        os.system(cmd)
    @staticmethod
    def blender_process_load_script(blenderExe : str, blenderFullPath : str, scriptFullPath : str, optionFullPath : str, inputPath : str, outputPath : str, saveName : str, bBackground : bool = False) :
        '''
        Desc
            - blender script를 통해 기존의 blend 파일을 로딩한다. 이때 추가로 새로운 stl 파일들을 import 한다. 
        Input 
            - blenderExe : option.json의 "BlenderExe" value
            - blenderFullPath : 로딩 할 blend 파일의 fullpath
            - scriptFullPath : blender가 실행해야 할 scirpt fullpath
            - optionFullPath : option.json의 fullpath
            - inputPath : import할 stl 파일들이 저장 된 folder path
            - outputPath : blend 파일이 저장 될 path
            - saveName : 저장 될 blend 파일명
            - bBackground : blender를 background로 실행 시킬 여부 지정 
        '''
        saveName = f"{saveName}.blend"
        if bBackground == False :
            cmd = f"{blenderExe} {blenderFullPath} --python {scriptFullPath} -- --optionFullPath {optionFullPath} --inputPath {inputPath} --outputPath {outputPath} --saveName {saveName}"
        else :
            cmd = f"{blenderExe} -b {blenderFullPath} --python {scriptFullPath} -- --optionFullPath {optionFullPath} --inputPath {inputPath} --outputPath {outputPath} --saveName {saveName}"
        os.system(cmd)

    s_phaseInfoFileName = "phaseInfo"


    def __init__(self, datainst : data.CData, mediator) :
        # input your code
        self.m_data = datainst
        self.m_mediator = mediator
    def clear(self) :
        self.m_data = None
        self.m_mediator = None
        # input your code
    
    
    # override
    def override_changed_optioninfo(self) :
        '''
        data에서 optioninfo가 바뀌었을 때 code 작성 
        '''
        pass
    def override_recon(self) :
        '''
        reconstruction code 작성
        '''
        pass
    def override_individual_recon(self, phaseinfo : dict) :
        '''
        개별 reconstruction code 작성
        
        ret
            - phaseinfo : dict
                - key -> phase : str
                - value -> listFullPath : list (nii.gz or zip)
                       
        '''
        pass
    def override_clean(self, patientID : str, outputPath : str) :
        '''
        clean code 작성 
        '''
        pass
    def override_load_centerline(self) :
        '''
        Main Tab에서 centerline button click시 작성 
        '''
        pass


    # protected
    def _copy_phaseinfo(self, targetPath : str, phaseinfo : dict) :
        for phase, listFullPath in phaseinfo.items() :
            folderPath = os.path.join(targetPath, phase)
            if not os.path.exists(folderPath) :
                os.makedirs(folderPath)

            for fullPath in listFullPath :
                lowerPath = fullPath.lower()

                if lowerPath.endswith(".nii.gz") :
                    shutil.copy(fullPath, folderPath)
                elif lowerPath.endswith(".zip") :
                    shutil.unpack_archive(fullPath, folderPath, "zip")
            
            self.__copy_child_folder_nifti(folderPath)
    

    # private 
    def __copy_child_folder_nifti(self, targetPath : str) :
        target = Path(targetPath)
        for item in target.iterdir() :
            if item.is_dir() :
                folderPath = str(item)
                self.__copy_nifti(targetPath, folderPath)
                shutil.rmtree(folderPath)
    def __copy_nifti(self, targetPath : str, folderPath : str) :
        target = Path(targetPath)
        target.mkdir(parents=True, exist_ok=True)
        
        for file in Path(folderPath).rglob("*.nii.gz"):
            shutil.copy2(file, target / file.name)


    @property
    def Data(self) -> data.CData :
        return self.m_data
    @property
    def Mediator(self) :
        return self.m_mediator

    

if __name__ == '__main__' :
    pass


# print ("ok ..")

