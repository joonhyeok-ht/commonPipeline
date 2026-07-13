import sys
import os
import numpy as np
import shutil
import vtk
import subprocess
import math
from collections import Counter

from PySide6.QtCore import Qt, QItemSelection, QItemSelectionModel
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QGroupBox, QWidget, QTreeView, QPushButton, QLineEdit, QLabel, QSizePolicy, QListWidget, QFileDialog, QFrame, QCheckBox, QTabWidget, QComboBox, QListWidgetItem, QMessageBox, QAbstractItemView
from PySide6.QtGui import QStandardItemModel, QStandardItem
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileAppPath = os.path.dirname(fileAbsPath)
fileToolPath = os.path.dirname(fileAppPath)
fileCommonPipelinePath = os.path.dirname(fileToolPath)

sys.path.append(fileAbsPath)
sys.path.append(fileAppPath)
sys.path.append(fileToolPath)
sys.path.append(fileCommonPipelinePath)

import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algSkeletonGraph as algSkeletonGraph
import AlgUtil.algMeshLib as algMeshLib
import AlgUtil.algVTK as algVTK

import clsignal as clsignal
import data as data
import operation as operation
import component as component
import componentSelectionCL as componentSelectionCL
import treeVessel as treeVessel

import VtkObj.vtkObjLine as vtkObjLine
import vtkObjInterface as vtkObjInterface

import command.commandKnife as commandKnife
import command.commandVesselKnife as commandVesselKnife


class CComSelectionCell(componentSelectionCL.CComDrag) :
    '''
    groupID : 0 고정
    ID : only 0, 1
    '''
    s_guideCellType = "guideCell"


    def __init__(self, mediator) :
        super().__init__(mediator)
        self.m_stateActive = -1
        self.m_selCellID = -1

        '''
        slot_click(selectionCellID : int)
        '''
        self.signal_click = clsignal.CSignal()
        '''
        slot_move(selectionCellID : int)
        '''
        self.signal_move = clsignal.CSignal()
    def clear(self) :
        self.m_stateActive = -1
        self.m_selCellID = -1
        self.signal_click.clear()
        self.signal_move.clear()
        super().clear()

    def ready(self) -> bool :
        return True
    def process_init(self) :
        super().process_init()
        # input your code
        if self.ready() == False :
            return
        
        self.set_state(0)
    def process_end(self) :
        # input your code
        if self.ready() == False :
            return
        
        self.set_state(0)
        super().process_end()

    def set_state(self, state : int) :
        '''
        state 
            - 0 : 선택하지 않는 상태
            - 1 : 선택할 수 있는 상태 
        
        '''
        # state exit
        if self.m_stateActive >= 0 :
            if self.m_stateActive == 0 :
                pass
            else :
                self.App.remove_key_type(CComSelectionCell.s_guideCellType)

        self.m_stateActive = state
        self.m_selCellID = -1

        # state start
        if self.m_stateActive >= 0 :
            if self.m_stateActive == 0 :
                pass
            else :
                self.m_picker = vtk.vtkCellPicker()
                self.m_picker.SetTolerance(0.0005)
                self.__create_guide_cell_key(0, algLinearMath.CScoMath.to_vec3([1.0, 0.9, 0.2]))
                self.__create_guide_cell_key(1, algLinearMath.CScoMath.to_vec3([0.0, 1.0, 0.0]))
                self.App.ref_key_type(CComSelectionCell.s_guideCellType)
        self.App.update_viewer()

    
    # mouse event
    def click(self, clickX : int, clickY : int, listExceptKeyType=None) -> bool :
        if self.ready() == False :
            return False
        super().click(clickX, clickY)

        if self.m_stateActive < 1 : 
            return
        
        guideCell = self.__get_guide_cell_obj(0)
        polyData = guideCell.PolyData
        if polyData is None :
            return
        
        guideCell = self.__get_guide_cell_obj(1)
        guideCell.PolyData = polyData

        self.signal_click.process(self.m_selCellID)
        
        return True
    def click_with_shift(self, clickX : int, clickY : int, listExceptKeyType=None) -> bool :
        if self.ready() == False :
            return False
        return True
    def release(self, clickX : int, clickY : int) :
        if self.ready() == False :
            return False
        return True
    def move(self, clickX : int, clickY : int, listExceptKeyType=None) :
        if self.ready() == False :
            return
        super().move(clickX, clickY, listExceptKeyType)

        if self.m_stateActive < 1 : 
            return
        
        if listExceptKeyType is None :
            listExceptKeyType = []
        listExceptKeyType.append(CComSelectionCell.s_guideCellType)

        self.m_selCellID = self.App.picking_cellid(clickX, clickY, listExceptKeyType)
        if self.m_selCellID <= 0 :
            self.signal_move.process(self.m_selCellID)
            return

        if self.m_selCellID > 0 :
            dataInst = self._get_data()
            clinfoInx = self._get_clinfoinx()

            vesselKey = data.CData.make_key(data.CData.s_vesselType, clinfoInx, 0)
            vesselObj = dataInst.find_obj_by_key(vesselKey)
            # 이 조건문은 걸리면 안되어야 함.. 만약 걸렸다면 무언가 잘못된거임 
            if vesselObj is None :
                return
            vesselPolyData = vesselObj.PolyData

            pickedPoly = algVTK.CVTK.get_sub_polydata_by_face_fast(vesselPolyData, [self.m_selCellID])
            retPoly = vtk.vtkPolyData()
            retPoly.DeepCopy(pickedPoly)
            guideCell = self.__get_guide_cell_obj(0)
            guideCell.PolyData = retPoly

            self.signal_move.process(self.m_selCellID)
 
        return True


    # private
    def __create_guide_cell_key(self, id : int, color : np.ndarray) -> str :
        guideKey = data.CData.make_key(CComSelectionCell.s_guideCellType, 0, id)
        guideObj = vtkObjInterface.CVTKObjInterface()
        guideObj.KeyType = CComSelectionCell.s_guideCellType
        guideObj.Key = guideKey
        guideObj.Color = color
        guideObj.Opacity = 1.0

        datainst = self._get_data()
        datainst.add_vtk_obj(guideObj)
        return guideKey
    def __get_guide_cell_obj(self, id : int) -> vtkObjInterface.CVTKObjInterface :
        guideKey = data.CData.make_key(CComSelectionCell.s_guideCellType, 0, id)
        dataInst = self._get_data()
        guideObj = dataInst.find_obj_by_key(guideKey)
        return guideObj
    

    @property
    def SelCellID(self) -> int :
        return self.m_selCellID
    
    
class CComSelectionCellUI(CComSelectionCell) :
    def __init__(self, mediator, uiTitle : str) :
        super().__init__(mediator)
        # input your code
        self.m_uiTitle = uiTitle
        self._init_groupbox()

        self.signal_click.add_slot(self.slot_click)
        self.signal_move.add_slot(self.slot_move)
    def clear(self) :
        # input your code
        self.m_uiTitle = ""
        super().clear()

    def ready(self) -> bool :
        return True
    def process_init(self) :
        super().process_init()
        # input your code
        if self.ready() == False :
            return
        
        self.setui_check_active(False)
    def process_end(self) :
        # input your code
        if self.ready() == False :
            return
        
        self.setui_check_active(False)
        
        super().process_end()

    def set_state(self, state : int) :
        super().set_state(state)
        # input your code 
        self.setui_label_cell_id(self.SelCellID)
        self.setui_cell_id(self.SelCellID)

    # ui
    def setui_check_active(self, bCheck : bool) -> bool :
        self.m_cbActive.setChecked(bCheck)
    def setui_cell_id(self, cellID : int) :
        self.m_editBoxCellID.blockSignals(False)
        self.m_editBoxCellID.setText(str(cellID))
        self.m_editBoxCellID.blockSignals(True)
    def setui_label_cell_id(self, cellID : int) :
        self.m_labelCellID.setText(f"Picking CellID : {cellID}")

    def getui_check_active(self) -> bool :
        if self.m_cbActive.isChecked() :
            return True
        return False
    def getui_cell_id(self) -> int :
        cellID = -1
        try :
            cellID = int(self.m_editBoxCellID.text())
        except ValueError:
            cellID = -1
        return cellID
    

    # protected
    def _init_groupbox(self) :
        self.m_gb = QGroupBox(self.m_uiTitle)
        layoutGB = QVBoxLayout()

        layout = QHBoxLayout()

        self.m_cbActive = QCheckBox("Active Selection")
        self.m_cbActive.setChecked(False)
        self.m_cbActive.stateChanged.connect(self._on_check_active)

        layout.addWidget(self.m_cbActive)
        layoutGB.addLayout(layout)

        self.m_labelCellID = QLabel("Picking CellID : ")
        self.m_labelCellID.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        self.m_labelCellID.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        layoutGB.addWidget(self.m_labelCellID)

        layout = QHBoxLayout()

        label = QLabel("CellID ")
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.m_editBoxCellID = QLineEdit()

        layout.addWidget(label)
        layout.addWidget(self.m_editBoxCellID)
        layoutGB.addLayout(layout)


        self.m_gb.setLayout(layoutGB)
    
    # ui event
    def _on_check_active(self, state) :
        '''
        state
            - 0 : unchecked
            - 1 : partially checked
            - 2 : checked
        '''
        if state == 2 :
            self.set_state(1)
        else :
            self.set_state(0)


    # slot
    def slot_click(self, selCellID : int) :
        self.setui_cell_id(selCellID)
    def slot_move(self, selCellID : int) :
        self.setui_label_cell_id(selCellID)


    @property
    def GroupBox(self) -> QGroupBox :
        return self.m_gb


if __name__ == '__main__' :
    pass


# print ("ok ..")

