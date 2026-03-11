import sys
import os
import numpy as np
import shutil
import vtk
import subprocess

from PySide6.QtCore import Qt, QItemSelectionModel, QModelIndex
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLineEdit, QLabel, QSizePolicy, QListWidget, QFileDialog, QFrame, QCheckBox, QTabWidget, QComboBox, QTableView, QMessageBox
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


import AlgUtil.algVTK as algVTK
import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algSkeletonGraph as algSkeletonGraph

import Block.optionInfo as optionInfo
import Block.niftiContainer as niftiContainer
import Block.reconstruction as reconstruction

import VtkObj.vtkObj as vtkObj
import vtkObjInterface as vtkObjInterface

import command.commandInterface as commandInterface
import command.commandLoadingPatient as commandLoadingPatient
import command.commandExtractionCL as commandExtractionCL
import command.commandRecon as commandRecon

import state.project.userData as userData

import data as data
import operation as op

import tabState as tabState

# kidney_batch
import makeInputFolderKidneyBatch as makeInputFolder


class CTabStateMain(tabState.CTabState) :
    s_guideCellType = "guideCell"
    '''
    groupID : 0 고정
    ID : only 0, 1
    '''
    s_listStepName = [
        "Recon",
        "Overlap",
        "Separate+MeshClean",
        "Centerline"
    ]
    s_intermediatePathAlias = "OutTemp"
    
    def __init__(self, mediator) :
        self.m_bReady = False
        self.m_listStepBtnEvent = [
            self._on_btn_recon,
            self._on_btn_overlap,
            self._on_btn_separate_and_clean,
            self._on_btn_centerline
        ]

        super().__init__(mediator)
        # input your code
        self.m_optionFullPath = ""
        self.m_bReady = True
    def clear(self) :
        # input your code
        self.m_optionFullPath = ""
        self.m_btnCL = None
        self.m_bReady = False
        super().clear()


    def process_init(self) :
        dataInst = self.get_data()
        if dataInst.Ready == False :
            print("not setting patient path")
            return
    def process(self) :
        pass
    def process_end(self) :
        dataInst = self.get_data()
        if dataInst.Ready == False :
            print("not setting patient path")
            return


    def init_ui(self) :
        tabLayout = QVBoxLayout()
        self.Tab.setLayout(tabLayout)

        # path ui
        label = QLabel("-- Path Info --")
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        tabLayout.addWidget(label)


        # def create_layout_label_editbox(self, title : str, bReadOnly : bool = False) -> tuple :
        # '''
        # ret : (QHBoxLayout, QLineEdit)
        # '''
        layout, self.m_editOptionPath, btn = self.m_mediator.create_layout_label_editbox_btn("Option", False, "..")
        btn.clicked.connect(self._on_btn_option_path)
        tabLayout.addLayout(layout)
        # sally
        layout, self.m_editInputPath, btn = self.m_mediator.create_layout_label_editbox_btn("Input", False, "..")
        btn.clicked.connect(self._on_btn_input_zip_path)
        tabLayout.addLayout(layout)

        # sally
        layout, self.m_editUnzipPath = self.m_mediator.create_layout_label_editbox("Output", False)
        tabLayout.addLayout(layout) 
        layout, self.m_editHuIDPath = self.m_mediator.create_layout_label_editbox("HuIDIn", False)
        tabLayout.addLayout(layout) 
        layout, self.m_editOutputPath = self.m_mediator.create_layout_label_editbox(f"{CTabStateMain.s_intermediatePathAlias}", False)
        tabLayout.addLayout(layout)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        tabLayout.addWidget(line)

        label = QLabel("-- Reconstruction STEP --")
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        tabLayout.addWidget(label)
        
        self.m_styleSheetBtn = """
            QPushButton {
                background-color: #1A73E8;
                color: white;
                font-weight: bold;
                border-radius: 5px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: red;
            }
        """
        layout, btnList = self.m_mediator.create_layout_btn_array(CTabStateMain.s_listStepName)
        for inx, stepName in enumerate(CTabStateMain.s_listStepName) :
            btnList[inx].clicked.connect(self.m_listStepBtnEvent[inx])
        tabLayout.addLayout(layout)
        self.m_btnCL = btnList[3] # btn 'Centerline'


        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        tabLayout.addWidget(line)

        label = QLabel("-- Centerline --")
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        tabLayout.addWidget(label)

        self.m_modelCLInfo = QStandardItemModel()
        self.m_modelCLInfo.setHorizontalHeaderLabels(["Index", "BlenderName", "Output"])
        self.m_tvCLInfo = QTableView()
        self.m_tvCLInfo.setModel(self.m_modelCLInfo)
        self.m_tvCLInfo.setEditTriggers(QTableView.NoEditTriggers)
        self.m_tvCLInfo.horizontalHeader().setStretchLastSection(True)
        self.m_tvCLInfo.verticalHeader().setVisible(False)
        self.m_tvCLInfo.setSelectionBehavior(QTableView.SelectRows)
        self.m_tvCLInfo.clicked.connect(self._on_tv_clicked_clinfo)
        tabLayout.addWidget(self.m_tvCLInfo)

        #sally
        btn = QPushButton("Do Blender")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_do_blender)
        tabLayout.addWidget(btn)
        
        btn = QPushButton("Extract Centerline")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_extract_centerline)
        tabLayout.addWidget(btn)

        
        btn = QPushButton("Wrap-Up")
        btn.setStyleSheet(self.m_styleSheetBtn)
        btn.clicked.connect(self._on_btn_wrap_up)
        tabLayout.addWidget(btn)

        lastUI = line
        tabLayout.setAlignment(lastUI, Qt.AlignmentFlag.AlignTop)

    
    def clicked_mouse_rb(self, clickX, clickY) :
        self.m_mediator.update_viewer()
    def mouse_move(self, clickX, clickY) :
        self.m_mediator.update_viewer()
    
    def changed_project_type(self) :
        optionFullPath = os.path.join(self.m_mediator.FilePath, "option.json")
        if os.path.exists(optionFullPath) == False :
            optionFullPath = os.path.join(self.m_mediator.CommonPipelinePath, "option.json")
            if os.path.exists(optionFullPath) == False :
                optionFullPath = ""
        self.command_option_path(optionFullPath)


    # ui 
    def setui_edit_input_path(self, inputPath : str) :
        self.m_editInputPath.setText(inputPath)
    def setui_edit_unzip_path(self, unzipPath : str) :
        self.m_editUnzipPath.setText(unzipPath)
    def setui_edit_huid_path(self, huidPath : str) :
        self.m_editHuIDPath.setText(huidPath)
    def setui_edit_option_path(self, optionPath : str) :
        self.m_editOptionPath.setText(optionPath)
    def setui_edit_outtemp_path(self, outtempPath : str) :
        self.m_editOutputPath.setText(outtempPath)
    
    def getui_edit_input_path(self) -> str :
        return self.m_editInputPath.text()
    def getui_edit_unzip_path(self) -> str :
        return self.m_editUnzipPath.text()
    def getui_edit_huid_path(self) -> str :
        return self.m_editHuIDPath.text()
    def getui_edit_option_path(self) -> str :
        return self.m_editOptionPath.text()
    def getui_edit_outtemp_path(self) -> str :
        return self.m_editOutputPath.text()
    

    # command
    def command_option_path(self, optionFullPath : str) :
        self._clear_data()
        datainst = self.get_data()

        self.setui_edit_input_path("")
        self.setui_edit_unzip_path("")
        self.setui_edit_huid_path("")
        self.setui_edit_outtemp_path("")

        if os.path.exists(optionFullPath) == False :
            QMessageBox.information(self.m_mediator, "Alarm", "not found option file")
            optionFullPath = ""
            datainst.OptionInfo = None
        else :
            optionInfoInst = optionInfo.COptionInfo(optionFullPath)
            datainst.OptionInfo = optionInfoInst
        self.setui_edit_option_path(optionFullPath)
        self.m_mediator.update_viewer()
    def command_input_zip_path(self, inputZipPath : str) :
        '''
        - 이 부분에서 반드시 data clear가 일어나야 되며, patientID와 outputTempPath가 세팅이 된 상태여야만 한다. 
        '''
        self._clear_patient_data()

        self.setui_edit_input_path(inputZipPath)
        self.setui_edit_unzip_path("")
        self.setui_edit_huid_path("")
        self.setui_edit_outtemp_path("")
        if inputZipPath == "" :
            return
        
        rootPath, huid = self._get_rootpath_huid(inputZipPath)
        self.setui_edit_unzip_path(rootPath)
        self.setui_edit_huid_path(huid)

        self.command_outtemp_path(rootPath)
        self.command_refresh_optioninfo()
        self.m_mediator.update_viewer()
    def command_outtemp_path(self, dataRootPath : str) :
        outputTempPath = os.path.join(os.path.dirname(dataRootPath), CTabStateMain.s_intermediatePathAlias)
        if os.path.exists(outputTempPath) == False :
            os.makedirs(outputTempPath, exist_ok=True)
        self.setui_edit_outtemp_path(outputTempPath)

        huid = self.getui_edit_huid_path()

        datainst = self.get_data()
        datainst.PatientID = huid
        datainst.OutputPath = outputTempPath

        self.m_mediator.set_title(huid)
        self.m_mediator.update_viewer()
    def command_refresh_optioninfo(self) :
        datainst = self.get_data()
        dataRootPath = self.getui_edit_unzip_path()
        patientID = self.getui_edit_huid_path()
        outputPath = datainst.OutputPath

        optioninfo = datainst.OptionInfo
        optioninfo.DataRootPath = dataRootPath

        # 지정된 folder에서 mask list를 얻어옴 

        phaseMaskList = []

        unzipPath = dataRootPath
        maskRoot = os.path.join(unzipPath, patientID, "02_SAVE", "01_MASK")
        apPath = os.path.join(maskRoot, "AP")
        ppPath = os.path.join(maskRoot, "PP")
        dpPath = os.path.join(maskRoot, "DP")
        list_ap = os.listdir(apPath)
        list_ap = [f.split('.')[0] for f in list_ap]
        list_pp = os.listdir(ppPath)
        list_pp = [f.split('.')[0] for f in list_pp]
        list_dp = os.listdir(dpPath)
        list_dp = [f.split('.')[0] for f in list_dp]
        phaseMaskList.append({'phase':'AP', 'files': list_ap})
        phaseMaskList.append({'phase':'PP', 'files': list_pp})
        phaseMaskList.append({'phase':'DP', 'files': list_dp})

        '''
        key : maskName
        value : phase
        '''
        dicMaskPhase = {}
        '''
        key : phase
        value : kidneyName
        '''
        dicKidneyPhase = {}
        tumorToken = 'Tumor_'
        kidneyToken = 'Kidney_'
        tumorPhase = ""
        # tumor phase 감지 
        # phase별 kidney name 감지 
        for maskinfo in phaseMaskList :
            phase = maskinfo['phase']
            listMask = maskinfo['files']
            for maskName in listMask :
                dicMaskPhase[maskName] = phase
                # tumor phase 감지 
                if tumorToken in maskName :
                    tumorPhase = phase
                if kidneyToken in maskName :
                    dicKidneyPhase[phase] = maskName

        # optioninfo mask의 phase refresh
        iCnt = optioninfo.get_recon_count()
        for reconInx in range(0, iCnt) :
            listCnt = optioninfo.get_recon_list_count(reconInx)
            for listInx in range(0, listCnt) :
                maskName, _, _, _ = optioninfo.get_recon_list(reconInx, listInx)
                phase = ""
                if maskName in dicMaskPhase :
                    phase = dicMaskPhase[maskName]
                if tumorToken in maskName :
                    phase = tumorPhase
                if maskName == "Kidney" :
                    phase = tumorPhase
                optioninfo.set_recon_phase(maskName, phase)

        # kidney registration refresh 
        targetKidney = ""
        listSrcKidney = []

        for key, value in dicKidneyPhase.items() :
            if key == tumorPhase :
                targetKidney = value
            else :
                listSrcKidney.append(value)

        optioninfo.clear_registrationinfo()
        if targetKidney != "" :
            for srcKidney in listSrcKidney :
                optioninfo.add_registrationinfo(targetKidney, srcKidney, 0)

        self.command_post_refresh_optioninfo()
    def command_post_refresh_optioninfo(self) :
        datainst = self.get_data()
        optioninfo = datainst.OptionInfo

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
        
    

    # protected 
    def _get_rootpath_huid(self, inputPath : str) -> tuple :
        '''
        ret 
            - (rootpath, huid)
            - rootpath : zip이 있는 path에서 dataRootPath가 생성 됨
            - huid : dataRootPath안에 huid 폴더가 생성 (기존 PatientID)
        '''
        rootpath = ''
        huid = ''
        mkInputFold = makeInputFolder.CMakeInputFolder()
        mkInputFold.ZipPath = inputPath
        mkInputFold.FolderMode = mkInputFold.eMode_Kidney 
        result = mkInputFold.process()
        if result == True :
            rootpath = mkInputFold.get_data_root_path()
            huid = mkInputFold.PatientID
            print(f"Making Input Folder Done. RootPath={rootpath}")
            
        return (rootpath, huid)
    def _clear_data(self) :
        datainst = self.get_data()
        self.m_mediator.remove_all_key()
        datainst.clear()
    def _clear_patient_data(self) :
        datainst = self.get_data()
        self.m_mediator.remove_all_key()
        datainst.clear_patient()
    def _get_tumor_phase_with_kidney_name(self, dataRootPath : str, patientID : str) :
        tumor_phase = ""
        target_kidney = "" # 정합의 기준이 되는 Kidney name
        tumor = "Tumor_" # Tumor_* 가 있는 phase 기준으로 정합 수행(exo, endo 상관없이)
        phaseMaskList = []

        unzipPath = dataRootPath
        maskRoot = os.path.join(unzipPath, patientID, "02_SAVE", "01_MASK")
        apPath = os.path.join(maskRoot, "Mask_AP")
        ppPath = os.path.join(maskRoot, "Mask_PP")
        dpPath = os.path.join(maskRoot, "Mask_DP")        
        list_ap = os.listdir(apPath)
        list_pp = os.listdir(ppPath)
        list_dp = os.listdir(dpPath)
        phaseMaskList.append({'phase':'AP', 'files': list_ap})
        phaseMaskList.append({'phase':'PP', 'files': list_pp})
        phaseMaskList.append({'phase':'DP', 'files': list_dp})
        print(f"PhaseMaskList : {phaseMaskList}")
        tumorfindFlag = False
        targetfindFlag = False
        for phaseMask in phaseMaskList :
            for mask in phaseMask['files'] :
                if tumor in mask :
                    tumor_phase = phaseMask['phase']
                    tumorfindFlag = True
                    break
            if tumorfindFlag :
                for mask in phaseMask['files'] :
                    if 'Kidney' in mask :
                        target_kidney = mask
                        targetfindFlag = True
                        break
            if targetfindFlag :
                break
        if not tumorfindFlag :
            return "", "", None, phaseMaskList
        
        directionAndExtention = target_kidney.split(f"_{tumor_phase[0]}")[1]  # "Kidney_AL.nii.gz" -> "L.nii.gz"
        phases = ['AP','PP','DP']
        phases.remove(tumor_phase)
        srcs = []  # registration시 src가 되는 kidney 
        srcs.append(f"Kidney_{phases[0][0]}{directionAndExtention}")
        srcs.append(f"Kidney_{phases[1][0]}{directionAndExtention}")
        print(f"Tumor Phase : {tumor_phase}, Target Kidney : {target_kidney}, Src Kidney : {srcs}")   

        return tumor_phase, target_kidney, srcs, phaseMaskList

    
    # ui event 
    def _on_btn_option_path(self) :
        self.m_btnCL.setEnabled(True)
        optionPath, _ = QFileDialog.getOpenFileName(self.get_main_widget(), "Select Option File", "", "JSON Files (*.json)")
        if optionPath == "" :
            return
        self.command_option_path(optionPath)
    def _on_btn_input_zip_path(self) :
        self.m_btnCL.setEnabled(True)
        datainst = self.get_data()
        if datainst.OptionInfo is None :
            QMessageBox.information(self.m_mediator, "Alarm", "please setting option file")
            return 

        inputPath = QFileDialog.getExistingDirectory(self.get_main_widget(), "Select Zip Folder")
        self.command_input_zip_path(inputPath)
    def _on_btn_recon(self) :
        if self.getui_edit_huid_path() == "" :
            print("not selection patientID")
            return
        if self.getui_edit_outtemp_path() == "" :
            print("not setting output path")
            return 
        
        userData = self.m_mediator.ReconUserData
        if userData is not None :
            userData.override_recon()
            QMessageBox.information(self.m_mediator, "Alarm", f"completed reconstruction")
        else :
            QMessageBox.information(self.m_mediator, "Alarm", f"failed reconstruction")
    def _on_btn_overlap(self) :
        pass
    def _on_btn_separate_and_clean(self) :
        pass
    def _on_btn_centerline(self) :
        dataInst = self.get_data()
        if dataInst.Ready == False :
            print("not setting option, outputPath, patientID")
            return
    def _on_btn_do_blender(self) :
        pass
    def _on_btn_extract_centerline(self) :
        pass
    def _on_btn_wrap_up(self) :
        pass
    def _on_cb_patientID_changed(self, index) :
        pass
    def _on_tv_clicked_clinfo(self, index) :
        dataInst = self.get_data()
        if dataInst.Ready == False :
            return
        # clinfoInx = self.getui_clinfo_inx()
        # if clinfoInx == -1 :
        #     return
        # dataInst.CLInfoIndex = clinfoInx
        

    # private


if __name__ == '__main__' :
    pass


# print ("ok ..")

