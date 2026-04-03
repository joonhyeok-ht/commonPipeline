import sys
import os
import numpy as np
import shutil
import glob
import vtk
import subprocess
import copy
import SimpleITK as sick
import datetime as dt
from pathlib import Path

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
import Block.makeInputFolder as makeInputFolder

import data as data

import userData as userData

import command.commandRecon as commandRecon
import commandReconKidneyBatch as commandReconKidneyBatch

import kbBlock.subDetectOverlap as detectOverlap


class CUserDataKB(userData.CUserData) :
    s_intermediatePathAlias = "OutTemp"


    def __init__(self, datainst : data.CData, mediator) :
        super().__init__(datainst, mediator)
        # input your code
        self.m_resPath = ""
        self.m_commonPath = ""
        self.m_scriptPath = ""
        self.m_reconScriptFullPath = ""
        self.m_individualReconScriptFullPath = ""
        self.m_sepCleanScriptFullPath = ""
        self.m_cleanScriptFullPath = ""

        self.m_movingBlenderPath = ""
        self.m_outputTempPath = ""
        self.m_outputTempPatientPath = ""
        self.m_localReconBlenderFullPath = ""
        self.m_localCleanBlenderFullPath = ""
        self.m_outputReconBlenderFullPath = ""
        self.m_outputOverlapBlenderFullPath = ""
        self.m_outputSepCleanBlenderFullPath = ""
        self.m_outputCleanBlenderFullPath = ""

        self.m_makeInputFolder = makeInputFolder.CMakeInputFolder()

        self.MovingBlenderPath = ""

        self.m_tumorPhase = ""
        self.m_anchorKidneyName = ""
        self.m_listExoName = []
    def clear(self) :
        # input your code
        self.m_resPath = ""
        self.m_commonPath = ""
        self.m_scriptPath = ""
        self.m_reconScriptFullPath = ""
        self.m_individualReconScriptFullPath = ""
        self.m_sepCleanScriptFullPath = ""
        self.m_cleanScriptFullPath = ""

        self.m_movingBlenderPath = ""
        self.m_outputTempPath = ""
        self.m_outputTempPatientPath = ""
        self.m_localReconBlenderFullPath = ""
        self.m_localCleanBlenderFullPath = ""
        self.m_outputReconBlenderFullPath = ""
        self.m_outputOverlapBlenderFullPath = ""
        self.m_outputSepCleanBlenderFullPath = ""
        self.m_outputCleanBlenderFullPath = ""

        self.m_makeInputFolder.clear()

        self.m_tumorPhase = ""
        self.m_anchorKidneyName = ""
        self.m_listExoName.clear()

        super().clear()

    def set_patient_zippath(self, zipPath : str) :
        self.MakeInputFolder.clear()
        self.MakeInputFolder.ZipPath = zipPath
        self.MakeInputFolder.process()

        dataRootPath = self.MakeInputFolder.DataRootPath
        patientID = self.MakeInputFolder.PatientID
        datainst = self.Data

        self.m_outputTempPath = ""
        self.m_outputTempPatientPath = ""

        if self.MakeInputFolder.Ready == True :
            # datainst refresh 
            self.m_outputTempPath = os.path.join(os.path.dirname(dataRootPath), CUserDataKB.s_intermediatePathAlias)
            self.m_outputTempPatientPath = os.path.join(self.m_outputTempPath, patientID)
            if os.path.exists(self.m_outputTempPath) == False :
                os.makedirs(self.m_outputTempPath, exist_ok=True)

            datainst.PatientID = patientID
            datainst.OutputPath = self.m_outputTempPath
            self.MovingBlenderPath = self.MakeInputFolder.BlenderSavePath
        else :
            datainst.PatientID = ""
            datainst.OutputPath = ""
            self.MovingBlenderPath = ""
            return
        
        self._refresh_optioninfo()
    

    # override
    def override_changed_optioninfo(self) :
        super().override_changed_optioninfo()

        # input your code
        if self.Data.OptionInfo is None :
            optioninfoPath = ""
        else :
            optioninfoPath = self.Data.OptionInfoPath

        self.m_resPath = os.path.join(optioninfoPath, "Res")
        self.m_commonPath = os.path.join(self.m_resPath, "common")
        self.m_scriptPath = os.path.join(self.m_resPath, "kidney_batch")
        self.m_reconScriptFullPath = os.path.join(self.m_scriptPath, "bspRecon.py")
        self.m_individualReconScriptFullPath = os.path.join(self.m_scriptPath, "bspIndRecon.py")
        self.m_sepCleanScriptFullPath = os.path.join(self.m_scriptPath, "bspSepClean.py")
        self.m_cleanScriptFullPath = os.path.join(self.m_commonPath, "bsmClean.py")

        self.MakeInputFolder.clear()

        self.m_movingBlenderPath = ""
        self.m_outputTempPath = ""
        self.m_outputTempPatientPath = ""
        self.m_localReconBlenderFullPath = ""
        self.m_localCleanBlenderFullPath = ""
        self.m_outputReconBlenderFullPath = ""
        self.m_outputOverlapBlenderFullPath = ""
        self.m_outputCleanBlenderFullPath = ""
    def override_recon(self) :
        datainst = self.Data
        optioninfo = datainst.OptionInfo
        folderinfo = self.MakeInputFolder

        # 기존에 존재할 경우 blender 로딩만 수행 
        if os.path.exists(self.OutputReconBlenderFullPath) == True :
            self.blender_process(self.OutputReconBlenderFullPath, None, None, False)
            return

        # dataRoot의 Mask를 OutTemp로 복사
        copiedMaskPath = os.path.join(datainst.OutputPatientPath, "Mask")
        if os.path.exists(self.OutputReconBlenderFullPath) == False :
            folderinfo.copy_mask(copiedMaskPath)
        reconStlPath = os.path.join(datainst.OutputPatientPath, "Result")

        # recon 수행 
        cmd = commandReconKidneyBatch.CCommandReconDevelopKidneyBatch(self.m_mediator)
        cmd.InputData = self.Data
        cmd.InputMaskPath = copiedMaskPath
        cmd.OutputPath = reconStlPath

        cmd.AnchorKidneyName = self.m_anchorKidneyName
        cmd.OutputKidneyName = "Kidney"
        for exoName in self.m_listExoName :
            cmd.add_exo_name(exoName)

        cmd.process()

        # blender 수행 
        # param 설정 
        '''
        param
            - "InputPath"       : import 할 mesh file들이 있는 folder  
            - "SaveFullPath"    : 저장 할 blend 파일명의 전체 경로
        '''
        dicParam = {
            "InputPath" : reconStlPath,
            "SaveFullPath" : self.m_localReconBlenderFullPath
        }
        scriptFullPath = self.m_reconScriptFullPath
        optionFullPath = self._blender_script_param(dicParam)
        self.blender_process(None, scriptFullPath, optionFullPath, False)

        # save blender folder로 move 
        if self.m_movingBlenderPath != "" :
            shutil.move(self.m_localReconBlenderFullPath, self.m_movingBlenderPath)
    def override_individual_recon(self, phaseinfo : dict) :
        datainst = self.Data
        optioninfo = datainst.OptionInfo
        folderinfo = self.MakeInputFolder

        tmpMaskPath = os.path.join(datainst.OutputPatientPath, "tmpMask")
        self._copy_phaseinfo(tmpMaskPath, phaseinfo)

        # targetMaskPath -> dataRoot Mask로 복사
        # dataRoot Mask -> OutTemp로 복사
        # optioninfo refresh
        copiedMaskPath = os.path.join(datainst.OutputPatientPath, "IndividualMask")
        for phase, _ in phaseinfo.items() :
            targetMaskPath = os.path.join(tmpMaskPath, phase)
            folderinfo.copy_target_mask(targetMaskPath, phase, copiedMaskPath)

        if os.path.exists(tmpMaskPath) == True :
            shutil.rmtree(tmpMaskPath)

        self._refresh_optioninfo()
        reconStlPath = os.path.join(datainst.OutputPatientPath, "IndividualResult")

        cmd = commandReconKidneyBatch.CCommandReconDevelopKidneyBatch(self.m_mediator)
        cmd.InputData = self.Data
        cmd.InputMaskPath = copiedMaskPath
        cmd.OutputPath = reconStlPath

        cmd.AnchorKidneyName = self.m_anchorKidneyName
        cmd.OutputKidneyName = "Kidney"
        for exoName in self.m_listExoName :
            cmd.add_exo_name(exoName)

        cmd.process()

        # blender 수행 
        # param 설정 
        '''
        param
            - "InputPath"       : import 할 mesh file들이 있는 folder  
        '''
        dicParam = {
            "InputPath" : reconStlPath
        }
        scriptFullPath = self.m_individualReconScriptFullPath
        optionFullPath = self._blender_script_param(dicParam)
        self.blender_process(self.OutputReconBlenderFullPath, scriptFullPath, optionFullPath, False)
        
        # clear
        if os.path.exists(copiedMaskPath) == True :
            shutil.rmtree(copiedMaskPath)
        if os.path.exists(reconStlPath) == True :
            shutil.rmtree(reconStlPath)
    def override_clean(self, blenderFullPath : str) :
        if os.path.exists(blenderFullPath) == False :
            return
        
        datainst = self.Data
        optioninfo = datainst.OptionInfo

        # 원본 blender는 복사 후 rename 
        shutil.copy2(blenderFullPath, self.OutputCleanBlenderFullPath)
        blenderFullPath = self.OutputCleanBlenderFullPath

        # blender 파일에 대해 import 수행 
        listStlPath = self._find_stl_path_from_out(datainst.OutputPatientPath)
        if len(listStlPath) > 0 :
            '''
            param
                - "StlPath"         : stl 파일들이 저장되어 있는 folder path, 없다면 "" 또는 None을 입력 
                - "ListStlFullPath  : stl파일들의 전체 경로를 저장한 list, 없다면 None을 입력 
            
            desc 
                - 기존 내용에 추가적으로 stl 파일들을 import 한다. 
            '''
            dicParam = {
                "StlPath" : None,
                "ListStlFullPath" : listStlPath
            }
            scriptPath = os.path.join(self.ResPath, "common")
            scriptFullPath = os.path.join(scriptPath, "bsmImportStl.py")
            optionFullPath = self._blender_script_param(dicParam)
            self.blender_process(blenderFullPath, scriptFullPath, optionFullPath, True)

        # blender 파일에 대해 clean 수행  
        # param 설정 
        '''
        param
            - "ListMeshName"    : clean-up 할 mesh name, None or 원소가 없다면 전체를 clean-up 한다.
            - "SaveFullPath"    : 저장 할 blend 파일명의 전체 경로, None or "" 라면 덮어쓴다. 
        '''
        dicParam = {
            "ListMeshName" : None,
            "SaveFullPath" : None
        }
        scriptFullPath = self.m_cleanScriptFullPath
        optionFullPath = self._blender_script_param(dicParam)
        self.blender_process(blenderFullPath, scriptFullPath, optionFullPath, False)
    def override_overlap(self, blenderFullPath : str) :
        if os.path.exists(blenderFullPath) == False :
            print("not found blender file")
            return
        
        datainst = self.Data
        optioninfo = datainst.OptionInfo
        
        # 원본 blender는 복사 후 rename 
        shutil.copy2(blenderFullPath, self.OutputOverlapBlenderFullPath)
        blenderFullPath = self.OutputOverlapBlenderFullPath

        listBlenderName = ["Ureter", "Renal_artery", "Renal_vein", "Abdominal_wall", "Gonadal_vein"]

        # blender 파일에서 listBlenderName 목록에 대해서만 clean 수행 
        # param 설정 
        '''
        param
            - "ListMeshName"    : clean-up 할 mesh name, None or 원소가 없다면 전체를 clean-up 한다.
            - "SaveFullPath"    : 저장 할 blend 파일명의 전체 경로, None or "" 라면 덮어쓴다. 
        '''
        dicParam = {
            "ListMeshName" : listBlenderName,
            "SaveFullPath" : None
        }
        scriptFullPath = self.m_cleanScriptFullPath
        optionFullPath = self._blender_script_param(dicParam)
        self.blender_process(blenderFullPath, scriptFullPath, optionFullPath, True)

        # export 
        exportPath = os.path.join(datainst.OutputPatientPath, "Overlap")
        self.blender_exporter(blenderFullPath, listBlenderName, exportPath)

        # overlap
        overlapinst = detectOverlap.CSubDetectOverlap()
        overlapinst.StlPath = exportPath
        overlapinst.LogPath = datainst.OutputPatientPath
        overlapinst.process()

        # import
        '''
        param
            - "StlPath"         : stl 파일들이 저장되어 있는 folder path, 없다면 "" 또는 None을 입력 
            - "ListStlFullPath  : stl파일들의 전체 경로를 저장한 list, 없다면 None을 입력 
        
        desc 
            - 기존 내용에 추가적으로 stl 파일들을 import 한다. 
        '''
        dicParam = {
            "StlPath" : exportPath,
            "ListStlFullPath" : None
        }
        scriptPath = os.path.join(self.ResPath, "common")
        scriptFullPath = os.path.join(scriptPath, "bsmImportStl.py")
        optionFullPath = self._blender_script_param(dicParam)
        self.blender_process(blenderFullPath, scriptFullPath, optionFullPath, False)

        # clear 
        if os.path.exists(exportPath) == True :
            shutil.rmtree(exportPath)
    def override_sep_clean(self, blenderFullPath : str) :
        if os.path.exists(blenderFullPath) == False :
            print("not found blender file")
            return
        
        # 원본 blender는 복사 후 rename 
        shutil.copy2(blenderFullPath, self.OutputSepCleanBlenderFullPath)
        blenderFullPath = self.OutputSepCleanBlenderFullPath


        listBlenderName = ["Kidney", "Renal_artery", "Renal_vein", "Ureter", "Rectus_*"]

        # blender 파일에서 listBlenderName 목록에 대해서만 clean 수행 
        # param 설정 
        '''
        param
            - "ListMeshName"    : clean-up 할 mesh name, None or 원소가 없다면 전체를 clean-up 한다.
            - "SaveFullPath"    : 저장 할 blend 파일명의 전체 경로, None or "" 라면 덮어쓴다. 
        '''
        dicParam = {
            "ListMeshName" : listBlenderName,
            "SaveFullPath" : None
        }
        scriptFullPath = self.m_cleanScriptFullPath
        optionFullPath = self._blender_script_param(dicParam)
        self.blender_process(blenderFullPath, scriptFullPath, optionFullPath, True)

        # separation & clean
        '''
        param
            - None
        warning : must be background mode
        '''
        dicParam = {}
        scriptFullPath = self.m_sepCleanScriptFullPath
        optionFullPath = self._blender_script_param(dicParam)
        self.blender_process(blenderFullPath, scriptFullPath, optionFullPath, True)

        # blender 실행 
        dicParam = {}
        optionFullPath = self._blender_script_param(dicParam)
        self.blender_process(blenderFullPath, None, optionFullPath, False)
    def override_load_centerline(self) :
        # 원본 blender는 복사 후 rename 
        shutil.copy2(blenderFullPath, self.OutputCleanBlenderFullPath)
        blenderFullPath = self.OutputCleanBlenderFullPath


        # protected 
    def _refresh_optioninfo(self) : 
        if self.MakeInputFolder.Ready == False : 
            return
        optioninfo = self.Data.OptionInfo
        if optioninfo is None :
            return
        
        folderInfo = self.MakeInputFolder
        maskPath = folderInfo.MaskPath
        self._collecting_collect_mask_phase(maskPath)

        dataRootPath = self.MakeInputFolder.DataRootPath

        optioninfo.reload()
        optioninfo.DataRootPath = dataRootPath

        # optioninfo mask의 phase refresh
        iCnt = optioninfo.get_recon_count()
        for reconInx in range(0, iCnt) :
            listCnt = optioninfo.get_recon_list_count(reconInx)
            for listInx in range(0, listCnt) :
                maskName, _, _, _ = optioninfo.get_recon_list(reconInx, listInx)
                phase = self._collecting_search_phase_of_maskname(maskName)
                optioninfo.set_recon_phase(maskName, phase)

        self._post_refresh_optioninfo()
    def _post_refresh_optioninfo(self) :
        datainst = self.Data
        optioninfo = datainst.OptionInfo

        tumorToken = 'Tumor'
        cystToken = 'Cyst'
        kidneyToken = 'Kidney_'

        self.m_tumorPhase = ""
        self.m_anchorKidneyName = ""
        self.m_listExoName.clear()
        
        self.m_tumorPhase = self._collecting_search_phase_of_maskname_keyword(tumorToken)
        if self.m_tumorPhase == "" :
            print("failed refresh option : not found tumor phase")
            return
        retList = self._collecting_search_maskname_in_phase(self.m_tumorPhase, kidneyToken)
        if retList is None :
            print("failed refresh option : not found kidney from tumor phase")
            return
        self.m_anchorKidneyName = retList[0]

        # cyst의 phase를 searching 한다음 tumor phase와 다르다면 resampling phase를 수행하도록 한다. 
        optioninfo.clear_resampling_phase()
        cystPhase = self._collecting_search_phase_of_maskname_keyword(cystToken)
        if cystPhase != "" and cystPhase != self.m_tumorPhase :
            retList = self._collecting_masknamelist_of_keyword(cystToken)
            if retList is not None :
                for cystname in retList :
                    # cyst name에 new keyword가 있을 경우 resampling 대상이므로 건너뛴다. 
                    if 'new' in cystname :
                        continue
                    inMaskName = cystname
                    outMaskName = f"{inMaskName}_new"
                    optioninfo.add_resampling_phase(inMaskName, outMaskName, self.m_tumorPhase)
                    optioninfo.set_recon_blendername(inMaskName, "")

                    if 'exo' in outMaskName :
                        self.m_listExoName.append(outMaskName)
        else :
            retList = self._collecting_masknamelist_of_keyword(cystToken)
            if retList is not None :
                for cystname in retList :
                    if 'new' in cystname :
                        continue
                    if 'exo' in cystname :
                        self.m_listExoName.append(cystname)

        # tumor exo setting
        retList = self._collecting_masknamelist_of_keyword(tumorToken)
        if len(retList) > 0 :
            for tumorname in retList :
                if 'exo' in tumorname :
                    self.m_listExoName.append(tumorname)
        
        # kidney phase setting
        optioninfo.set_recon_phase("Kidney", self.m_tumorPhase)

        # registration setting
        optioninfo.clear_registrationinfo()
        listKidney = self._collecting_masknamelist_of_keyword(kidneyToken)
        if len(listKidney) > 0 :
            for kidneyName in listKidney :
                if kidneyName == self.m_anchorKidneyName :
                    continue
                optioninfo.add_registrationinfo(self.m_anchorKidneyName, kidneyName, 0)

        # ResamplingToPhase 
        iCnt = optioninfo.get_resampling_phase_count()
        for inx in range(0, iCnt) :
            _, outMaskName, phase = optioninfo.get_resampling_phase(inx)
            optioninfo.set_recon_phase(outMaskName, phase)
        # ResamplingToMinSpacing 
        iCnt = optioninfo.get_resampling_minspacing_count()
        for inx in range(0, iCnt) :
            inMaskName, outMaskName = optioninfo.get_resampling_minspacing(inx)
            inPhase = optioninfo.find_phase_of_mask(inMaskName)
            optioninfo.set_recon_phase(outMaskName, inPhase)
        # Stricture 
        iCnt = optioninfo.get_stricture_count()
        for inx in range(0, iCnt) :
            inMaskName, outMaskName = optioninfo.get_stricture(inx)
            inPhase = optioninfo.find_phase_of_mask(inMaskName)
            optioninfo.set_recon_phase(outMaskName, inPhase)
        # Diaphragm
        skinPhase = optioninfo.find_phase_of_mask("Skin")
        optioninfo.set_recon_phase("Diaphragm", skinPhase)

        optioninfo.process_phase_alignment()


    @property
    def Data(self) -> data.CData :
        return self.m_data
    @property
    def MovingBlenderPath(self) -> str :
        return self.m_movingBlenderPath
    @MovingBlenderPath.setter
    def MovingBlenderPath(self, movingBlenderPath : str) :
        folderInfo = self.MakeInputFolder
        patientID = folderInfo.PatientID

        self.m_movingBlenderPath = movingBlenderPath

        # saveName = f"{patientID}_recon_{timestr}"
        saveName = f"{patientID}_recon"
        self.m_localReconBlenderFullPath = os.path.join(self.OutputTempPatientPath, f"{saveName}.blend")
        if self.m_movingBlenderPath == "" :
            self.m_outputReconBlenderFullPath = self.m_localReconBlenderFullPath
        else :
            self.m_outputReconBlenderFullPath = os.path.join(self.m_movingBlenderPath, f"{saveName}.blend")
        
        saveName = f"{patientID}_overlap"
        dirPath = os.path.dirname(self.m_outputReconBlenderFullPath)
        self.m_outputOverlapBlenderFullPath = os.path.join(dirPath, f"{saveName}.blend")

        saveName = f"{patientID}_sep_clean"
        dirPath = os.path.dirname(self.m_outputReconBlenderFullPath)
        self.m_outputSepCleanBlenderFullPath = os.path.join(dirPath, f"{saveName}.blend")

        saveName = f"{patientID}"
        self.m_localCleanBlenderFullPath = os.path.join(self.OutputTempPatientPath, f"{saveName}.blend")
        if self.m_movingBlenderPath == "" :
            self.m_outputCleanBlenderFullPath = self.m_localCleanBlenderFullPath
        else :
            self.m_outputCleanBlenderFullPath = os.path.join(self.m_movingBlenderPath, f"{saveName}.blend")
    @property
    def OutputTempPath(self) -> str :
        return self.m_outputTempPath
    @property
    def OutputTempPatientPath(self) -> str :
        return self.m_outputTempPatientPath
    @property
    def OutputReconBlenderFullPath(self) -> str :
        return self.m_outputReconBlenderFullPath
    @property
    def OutputOverlapBlenderFullPath(self) -> str :
        return self.m_outputOverlapBlenderFullPath
    @property
    def OutputSepCleanBlenderFullPath(self) -> str :
        return self.m_outputSepCleanBlenderFullPath
    @property
    def OutputCleanBlenderFullPath(self) -> str :
        return self.m_outputCleanBlenderFullPath
    @property
    def MakeInputFolder(self) -> makeInputFolder.CMakeInputFolder :
        return self.m_makeInputFolder
    




    

if __name__ == '__main__' :
    pass


# print ("ok ..")

