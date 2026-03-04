import sys
import os
import numpy as np
import shutil
import vtk
import subprocess
from matplotlib import cm

from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QPushButton, QWidget, QListWidget, QListWidgetItem
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

import vtkObjInterface as vtkObjInterface
import VtkObj.vtkObjText as vtkObjText

import data as data
import operation as operation
import component as component
# import territory as territory


class CComDrag(component.CCom) :
    def __init__(self, mediator) :
        super().__init__(mediator)
        self.m_startX = 0
        self.m_startY = 0
        self.m_endX = 0
        self.m_endY = 0
        self.m_bDrag = False
    def clear(self) :
        self.m_startX = 0
        self.m_startY = 0
        self.m_endX = 0
        self.m_endY = 0
        self.m_bDrag = False
        super().clear()


    # override
    def click(self, clickX : int, clickY : int, listExceptKeyType=None) -> bool :
        self.m_startX = clickX
        self.m_startY = clickY
        self.m_endX = clickX
        self.m_endY = clickY
        return True
    def click_with_shift(self, clickX : int, clickY : int, listExceptKeyType=None) -> bool :
        self.m_startX = clickX
        self.m_startY = clickY
        self.m_endX = clickX
        self.m_endY = clickY
        return True
    def release(self, clickX : int, clickY : int) :
        self.m_endX = clickX
        self.m_endY = clickY
        return True
    def move(self, clickX : int, clickY : int, listExceptKeyType=None) :
        self.m_endX = clickX
        self.m_endY = clickY
        return True
    

    @property
    def Drag(self) -> bool :
        return self.m_bDrag
    

class CComDragFindCL(CComDrag) :
    def __init__(self, mediator) :
        '''
        desc 
            find dragged centerline
        '''
        super().__init__(mediator)
        # input your code
        self.m_inputOPDragSelCL = None
        self.m_rt = None
        self.m_actorRt = self._create_rt_actor()
    def clear(self) :
        # input your code
        self.m_inputOPDragSelCL = None
        super().clear()

    def ready(self) -> bool :
        if self.InputOPDragSelCL is None :
            return False
        return True
    def process_init(self) :
        super().process_init()
        # input your code
    def process_end(self) :
        # input your code
        super().process_end()
    def click(self, clickX : int, clickY : int, listExceptKeyType=None) -> bool :
        if self.ready() == False :
            return False
        
        super().click(clickX, clickY, listExceptKeyType)
        self.InputOPDragSelCL.process_reset()
        renderer = self._get_renderer()
        renderer.AddActor2D(self.m_actorRt)
        self._update_rt_actor()

        self.m_bDrag = True
        return True
    def click_with_shift(self, clickX : int, clickY : int, listExceptKeyType=None) -> bool :
        if self.ready() == False :
            return False
        
        super().click_with_shift(clickX, clickY, listExceptKeyType)
        renderer = self._get_renderer()
        renderer.AddActor2D(self.m_actorRt)
        self._update_rt_actor()

        self.m_bDrag = True
        return True
    def release(self, clickX : int, clickY : int) :
        if self.ready() == False :
            return False
        if self.Drag == False :
            return False

        renderer = self._get_renderer()
        renderer.RemoveActor2D(self.m_actorRt)
        self.m_bDrag = False
        return True
    def move(self, clickX : int, clickY : int, listExceptKeyType=None) :
        if self.ready() == False :
            return
        if self.Drag == False :
            return False
        
        super().move(clickX, clickY, listExceptKeyType)
        self._update_rt_actor()
        return True
    

    def find_selection_clid(self) -> list :
        '''
        ret : [clID0, clID1, .. ]
        '''
        xmin, xmax = sorted([self.m_startX, self.m_endX])
        ymin, ymax = sorted([self.m_startY, self.m_endY])

        npPt = self.App.project_points_to_display(self._get_skeleton().m_listKDTreeAnchor)
        inside = ((npPt[:,0] >= xmin) & (npPt[:,0] <= xmax) & (npPt[:,1] >= ymin) & (npPt[:,1] <= ymax))
        selectedIndex = np.where(inside)[0]

        listID = set()
        for inx in selectedIndex :
            listID.add(self._get_skeleton().m_listKDTreeAnchorID[inx])
        
        listID = list(listID)
        if len(listID) == 0 :
            return None
        return listID
    

    # protected
    def _create_rt_actor(self) :
        self.m_rt = vtk.vtkPoints()
        self.m_rt.SetNumberOfPoints(4)
        for i in range(4):
            self.m_rt.SetPoint(i, 0, 0, 0)

        rect_poly = vtk.vtkPolyData()
        rect_poly.SetPoints(self.m_rt)

        rect_cells = vtk.vtkCellArray()
        rect_cells.InsertNextCell(5)
        for i in [0, 1, 2, 3, 0]:
            rect_cells.InsertCellPoint(i)
        rect_poly.SetLines(rect_cells)

        mapper = vtk.vtkPolyDataMapper2D()
        mapper.SetInputData(rect_poly)

        actor = vtk.vtkActor2D()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(0.3, 1.0, 0.3)
        actor.GetProperty().SetLineWidth(2.0)
        return actor
    def _update_rt_actor(self) :
        x0 = self.m_startX
        y0 = self.m_startY
        x1 = self.m_endX
        y1 = self.m_endY
        self.m_rt.SetPoint(0, x0, y0, 0)
        self.m_rt.SetPoint(1, x1, y0, 0)
        self.m_rt.SetPoint(2, x1, y1, 0)
        self.m_rt.SetPoint(3, x0, y1, 0)
        self.m_rt.Modified()
    

    @property
    def InputOPDragSelCL(self) -> operation.COperationDragSelectionCL :
        return self.m_inputOPDragSelCL
    @InputOPDragSelCL.setter
    def InputOPDragSelCL(self, opCL : operation.COperationDragSelectionCL) :
        self.m_inputOPDragSelCL = opCL

    

class CComDragSelCL(CComDragFindCL) :
    def __init__(self, mediator):
        '''
        desc 
            hier selection centerline component
        '''
        super().__init__(mediator)
        # input your code
        self.m_inputUIRBSelSingle = None
        self.m_inputUIRBSelDescendant = None
    def clear(self) :
        # input your code
        self.m_inputUIRBSelSingle = None
        self.m_inputUIRBSelDescendant = None
        super().clear()

    
    # event override 
    def ready(self) -> bool :
        if super().ready() == False :
            return False
        if self.InputUIRBSelSingle is None :
            return False
        if self.InputUIRBSelDescendant is None :
            return False
        return True
    def process_init(self) :
        super().process_init()
        # input your code
    def process_end(self) :
        # input your code
        super().process_end()
    def release(self, clickX : int, clickY : int) :
        if self.ready() == False :
            return False
        if self.Drag == False :
            return False
        
        super().release(clickX, clickY)

        if self.InputUIRBSelSingle.isChecked() : 
            self.InputOPDragSelCL.ChildSelectionMode = False
        elif self.InputUIRBSelDescendant.isChecked() :
            self.InputOPDragSelCL.ChildSelectionMode = True

        clinfoInx = self._get_clinfoinx()
        listCLID = self.find_selection_clid()
        listKey = []
        if listCLID is not None :
            for clID in listCLID :
                pickingKey = data.CData.make_key(data.CData.s_skelTypeCenterline, clinfoInx, clID)
                listKey.append(pickingKey)
            self.InputOPDragSelCL.add_selection_keys(listKey)
            self.InputOPDragSelCL.process()

        return True


    # protected


    @property
    def InputUIRBSelSingle(self) :
        return self.m_inputUIRBSelSingle
    @InputUIRBSelSingle.setter
    def InputUIRBSelSingle(self, inputUIRBSelSingle) :
        self.m_inputUIRBSelSingle = inputUIRBSelSingle
    @property
    def InputUIRBSelDescendant(self) :
        return self.m_inputUIRBSelDescendant
    @InputUIRBSelDescendant.setter
    def InputUIRBSelDescendant(self, inputUIRBSelDescendant) :
        self.m_inputUIRBSelDescendant = inputUIRBSelDescendant



class CComDragSelCLLabel(CComDragSelCL) :
    def __init__(self, mediator) :
        '''
        desc 
            selection centerline labeling component
        '''
        super().__init__(mediator)
        # input your code
    def clear(self) :
        # input your code
        super().clear()

    
    # event override 
    def process_init(self) :
        if self.ready() == False :
            return
        super().process_init()
        # input your code
        self._init_cl_label()
    def process_end(self) :
        if self.ready() == False :
            return
        # input your code
        self._clear_cl_label()
        super().process_end()

    
    # command
    def command_label_name(self, labelName : str) -> bool :
        if self.ready() == False :
            return False
        
        # selection clID 얻어옴
        # 해당 cl에 대해 labelName setting 
        listCLID = self.InputOPDragSelCL.get_all_selection_cl()
        if listCLID is None : 
            return False
        
        skeleton = self._get_skeleton()
        clinfoinx = self._get_clinfoinx()

        for clID in listCLID :
            cl = skeleton.get_centerline(clID)
            cl.Name = labelName
            clKey = data.CData.make_key(data.CData.s_skelTypeCenterline, clinfoinx, clID)
            self._update_cl_label(clKey)
        return True
    

    def _init_cl_label(self) :
        dataInst = self._get_data()
        clinfoInx = self._get_clinfoinx()
        skeleton = self._get_skeleton()

        labelColor = algLinearMath.CScoMath.to_vec3([1.0, 0.0, 0.0])
        iCnt = skeleton.get_centerline_count()
        for inx in range(0, iCnt) :
            cl = skeleton.get_centerline(inx)
            iCLInx = int(cl.get_vertex_count() / 2)
            pos = cl.get_vertex(iCLInx)
            activeCamera = self.App.get_active_camera()
            clName = cl.Name

            key = data.CData.make_key(data.CData.s_textType, 0, cl.ID)
            vtkText = vtkObjText.CVTKObjText(activeCamera, pos, clName, 1.0)
            vtkText.KeyType = data.CData.s_textType
            vtkText.Key = key
            vtkText.Color = labelColor
            dataInst.add_vtk_obj(vtkText)
        
        self.App.ref_key_type(data.CData.s_textType)
    def _clear_cl_label(self) :
        self.App.remove_key_type(data.CData.s_textType)
    def _update_cl_label(self,  clKey : str) :
        dataInst = self._get_data()
        clinfoInx = self._get_clinfoinx()
        skeleton = self._get_skeleton()

        keyType, groupID, clID = data.CData.get_keyinfo(clKey)
        cl = skeleton.get_centerline(clID)

        textKey = data.CData.make_key(data.CData.s_textType, 0, cl.ID)
        textObj = dataInst.find_obj_by_key(textKey)
        if textObj is not None :
            textObj.Text = cl.Name




class CTPInfo :
    def __init__(self) :
        self.m_label = ""
        self.m_pos = None
        self.m_color = None
        self.m_tpKey = ""
        self.m_tpLabelKey = ""
    def clear(self) :
        self.m_label = ""
        self.m_pos = None
        self.m_color = None
        self.m_tpKey = ""
        self.m_tpLabelKey = ""
    

    @property
    def Label(self) -> str :
        return self.m_label
    @Label.setter
    def Label(self, label : str) :
        self.m_label = label
    @property
    def Pos(self) -> np.ndarray :
        return self.m_pos
    @Pos.setter
    def Pos(self, pos : np.ndarray) :
        self.m_pos = pos
    @property
    def Color(self) -> np.ndarray :
        return self.m_color
    @Color.setter
    def Color(self, color : np.ndarray) :
        self.m_color = color
    @property
    def TPKey(self) -> str :
        return self.m_tpKey
    @TPKey.setter
    def TPKey(self, tpKey : str) :
        self.m_tpKey = tpKey
    @property
    def TPLabelKey(self) -> str :
        return self.m_tpLabelKey
    @TPLabelKey.setter
    def TPLabelKey(self, tpLabelKey : str) :
        self.m_tpLabelKey = tpLabelKey


class CComDragSelCLTP(CComDrag) :
    '''
    desc
        tp를 통해 centerline을 선택한다.. 
        반드시 add_tpinfo를 등록한 후에 사용한다. 등록 안할 시 동작 안함 
    '''
    s_tpColorCnt = 100
    s_tpVesselKeyType = "TPVessel"
    s_tpRadius = 1.5
    s_tpOpacity = 0.2
    s_pickingDepth = 1000.0
    s_tpLabelGroupID = 9999
    s_textGroupID = 10000


    def __init__(self, mediator) :
        '''
        desc 
            selection centerline component
        '''
        super().__init__(mediator)
        # input your code
        self.m_inputUILVTP = None
        '''
        value : {tpName, pos : np.ndarray}
        '''
        self.m_tpID = 0     # 누적된 TPID 
        self.m_listTPInfo = []
        '''
        key : tpVesselObj Key
        value : clID
        '''
        self.m_dicMatching = {}
        self.m_colors = np.array([cm.get_cmap("hsv", CComDragSelCLTP.s_tpColorCnt)(i)[:3] for i in range(CComDragSelCLTP.s_tpColorCnt)])

        self.m_selectedTPInfo = None
        self.m_ratio = 0.0

        self.m_comDragFindCL = CComDragFindCL(mediator)
    def clear(self) :
        # input your code
        self.m_inputUILVTP = None

        self.m_selectedTPInfo = None
        self.m_ratio = 0.0

        self.m_listTPInfo.clear()
        self.m_dicMatching.clear()
        self.m_colors = None

        self.m_comDragFindCL.clear()
        super().clear()

    
    # event override 
    def ready(self) -> bool :
        if self.m_comDragFindCL.ready() == False :
            return False
        if self.InputUILVTP is None :
            return False
        return True
    def process_init(self) :
        if self.ready() == False :
            return
        super().process_init()
        # input your code
        self.m_selectedTPInfo = None
        self.m_comDragFindCL.process_init()
        self.InputUILVTP.itemClicked.connect(self._on_lv_selection_tp)
    def process_end(self) :
        if self.ready() == False :
            return
        # input your code
        self.InputUILVTP.itemClicked.disconnect(self._on_lv_selection_tp)
        self.m_comDragFindCL.process_end()
        self.m_selectedTPInfo = None
        self.clear_tpinfo()
        self._clear_clobj_color()
        self._setui_lv_remove_all_tp()
        self.App.remove_key_type_groupID(data.CData.s_textType, CComDragSelCLTP.s_textGroupID)
        super().process_end()

    def get_tp_color(self, inx : int) -> np.ndarray :
        mappedIndex = inx % CComDragSelCLTP.s_tpColorCnt
        return self.m_colors[mappedIndex].reshape(-1, 3)
    def add_tpinfo(self, tpLabel : str, tpPos : np.ndarray) :
        datainst = self._get_data()
        activeCamera = self.App.get_active_camera()

        tpinfo = CTPInfo()
        tpinfo.Label = tpLabel
        tpinfo.Pos = tpPos

        keyType = CComDragSelCLTP.s_tpVesselKeyType
        tpID = self.m_tpID
        tpKey = data.CData.make_key(keyType, 0, tpID)
        tpColor = self.get_tp_color(tpID)
        tpPolydata = algVTK.CVTK.create_poly_data_sphere(
                algLinearMath.CScoMath.to_vec3([0.0, 0.0, 0.0]), 
                CComDragSelCLTP.s_tpRadius
            )

        tpVesselObj = vtkObjInterface.CVTKObjInterface()
        tpVesselObj.KeyType = keyType
        tpVesselObj.Key = tpKey
        tpVesselObj.Color = tpColor
        tpVesselObj.Opacity = CComDragSelCLTP.s_tpOpacity
        tpVesselObj.PolyData = tpPolydata
        tpVesselObj.Pos = tpPos
        datainst.add_vtk_obj(tpVesselObj)

        tpLabelPos = tpPos.copy()
        tpLabelPos[0, 1] = tpLabelPos[0, 1] + CComDragSelCLTP.s_tpRadius
        textKey = data.CData.make_key(data.CData.s_textType, CComDragSelCLTP.s_tpLabelGroupID, tpID)
        vtkText = vtkObjText.CVTKObjText(activeCamera, tpPos, tpLabel, 2.0)
        vtkText.KeyType = data.CData.s_textType
        vtkText.Key = textKey
        vtkText.Color = tpColor
        datainst.add_vtk_obj(vtkText)

        tpinfo.Color = tpColor
        tpinfo.TPKey = tpKey
        tpinfo.TPLabelKey = textKey
        self.m_listTPInfo.append(tpinfo)

        self._setui_lv_add_tp(tpinfo)

        self.App.ref_key(tpKey)
        self.App.ref_key(textKey)
        self.m_tpID += 1

        self.__attach_tpinfo_cl(tpinfo)
    def get_tpinfo_count(self) -> int :
        return len(self.m_listTPInfo)
    def get_tpinfo(self, inx : int) -> CTPInfo :
        return self.m_listTPInfo[inx]
    def find_tpinfo_of_label(self, tpLabel : str) -> CTPInfo :
        iCnt = self.get_tpinfo_count()
        for inx in range(0, iCnt) :
            tpinfo = self.get_tpinfo(inx)
            if tpinfo.Label == tpLabel :
                return tpinfo
        return None
    def find_tpinfo_of_tpkey(self, tpKey : str) -> CTPInfo :
        iCnt = self.get_tpinfo_count()
        for inx in range(0, iCnt) :
            tpinfo = self.get_tpinfo(inx)
            if tpinfo.TPKey == tpKey :
                return tpinfo
        return None
    def get_tpinfo_obj(self, tpinfo : CTPInfo) -> vtkObjInterface.CVTKObjInterface :
        dataInst = self._get_data()
        return dataInst.find_obj_by_key(tpinfo.TPKey)
    def get_tpinfo_text_obj(self, tpinfo : CTPInfo) -> vtkObjText.CVTKObjText :
        dataInst = self._get_data()
        return dataInst.find_obj_by_key(tpinfo.TPLabelKey)
    def clear_tpinfo(self) :
        iCnt = self.get_tpinfo_count()
        for inx in range(0, iCnt) :
            # tpinfo와 disconn을 하지 않음에 주의한다. 
            tpinfo = self.get_tpinfo(inx)
            self.App.remove_key(tpinfo.TPKey)
            self.App.remove_key(tpinfo.TPLabelKey)
        self._setui_lv_remove_all_tp()
    def remove_tpinfo_of_label(self, tpLabel : str) :
        tpinfo = self.find_tpinfo_of_label(tpLabel)
        if tpinfo is None :
            return
        self.__disconn_tpinfo_cl(tpinfo)
        self.m_listTPInfo.remove(tpinfo)
        self.App.remove_key(tpinfo.TPKey)
        self.App.remove_key(tpinfo.TPLabelKey)
        self._setui_lv_remove_tp(tpinfo)
    
    def refresh_cl_text(self) :
        self.App.remove_key_type_groupID(data.CData.s_textType, CComDragSelCLTP.s_textGroupID)

        dataInst = self._get_data()
        skeleton = self._get_skeleton()
        iCnt = skeleton.get_centerline_count()

        for clID in range(0, iCnt) :
            cl = skeleton.get_centerline(clID)
            if cl.Name == "" :
                continue
            if cl.ID in self.m_dicMatching.values() :
                continue

            iCLInx = int(cl.get_vertex_count() / 2)
            pos = cl.get_vertex(iCLInx)
            activeCamera = self.App.get_active_camera()

            key = data.CData.make_key(data.CData.s_textType, CComDragSelCLTP.s_textGroupID, clID)

            vtkText = vtkObjText.CVTKObjText(activeCamera, pos, cl.Name, 1.0)
            vtkText.KeyType = data.CData.s_textType
            vtkText.Key = key
            vtkText.Color = algLinearMath.CScoMath.to_vec3([1.0, 0.0, 0.0])
            dataInst.add_vtk_obj(vtkText)
        self.App.ref_key_type(data.CData.s_textType)
        

    def click(self, clickX : int, clickY : int, listExceptKeyType=None) -> bool :
        if self.ready() == False :
            return False
        
        super().click(clickX, clickY, listExceptKeyType)

        if self.m_selectedTPInfo is not None :
            tpinfoObj = self.get_tpinfo_obj(self.m_selectedTPInfo)
            tpinfoObj.Opacity = CComDragSelCLTP.s_tpOpacity
        self.m_selectedTPInfo = None
        self._setui_lv_clear_selection_tp()


        key = self.App.picking(clickX, clickY, listExceptKeyType)
        if key == "" :
            self.m_bDrag = True
            self.m_comDragFindCL.click(clickX, clickY, listExceptKeyType)
            self.command_reset_color()
            return True
        
        keyType = data.CData.get_type_from_key(key)
        if keyType != CComDragSelCLTP.s_tpVesselKeyType :
            return False
        tpinfo = self.find_tpinfo_of_tpkey(key)
        if tpinfo is None :
            return False
        
        self.command_reset_color()
        
        self.m_selectedTPInfo = tpinfo
        tpinfoObj = self.get_tpinfo_obj(tpinfo)
        tpinfoObj.Opacity = 1.0
        tpinx = self._getui_lv_find_tpinx(tpinfo)
        if tpinx >= 0 :
            self._setui_lv_selection_tp(tpinx)

        clickedPoint = self.App.picking_intersected_point(clickX, clickY, listExceptKeyType)
        if clickedPoint is not None :
            cameraInfo = self.App.get_active_camerainfo()
            cameraPos = cameraInfo[3]
            dist = algLinearMath.CScoMath.vec3_len(clickedPoint - cameraPos)
            self.m_ratio = dist / CComDragSelCLTP.s_pickingDepth

        self.m_bDrag = True
        return True
    def click_with_shift(self, clickX : int, clickY : int, listExceptKeyType=None) -> bool :
        if self.ready() == False :
            return False
        
        if self.m_selectedTPInfo is not None :
            tpinfoObj = self.get_tpinfo_obj(self.m_selectedTPInfo)
            tpinfoObj.Opacity = CComDragSelCLTP.s_tpOpacity
        self.m_selectedTPInfo = None
        self._setui_lv_clear_selection_tp()
        
        super().click_with_shift(clickX, clickY, listExceptKeyType)
        self.m_comDragFindCL.click_with_shift(clickX, clickY, listExceptKeyType)
        self.m_bDrag = True
        return True
    def release(self, clickX : int, clickY : int) :
        if self.ready() == False :
            return False
        if self.Drag == False :
            return False
        
        if self.m_selectedTPInfo is None :
            clinfoinx = self._get_clinfoinx()
            self.m_comDragFindCL.release(clickX, clickY)
            listCLID = self.m_comDragFindCL.find_selection_clid()
            if listCLID is not None :
                listValidCLKey = []
                for clID in listCLID :
                    if clID in self.m_dicMatching.values() :
                        continue
                    clKey = data.CData.make_key(data.CData.s_skelTypeCenterline, clinfoinx, clID)
                    listValidCLKey.append(clKey)
                self.m_comDragFindCL.InputOPDragSelCL.add_selection_keys(listValidCLKey)
                self.m_comDragFindCL.InputOPDragSelCL.process()
        else :
            self.refresh_cl_text()
        self.m_bDrag = False
        return True
    def move(self, clickX : int, clickY : int, listExceptKeyType=None) :
        if self.ready() == False :
            return False
        if self.Drag == False :
            return False
        
        super().move(clickX, clickY, listExceptKeyType)

        if self.m_selectedTPInfo is None :
            self.m_comDragFindCL.move(clickX, clickY, listExceptKeyType)
            return True
        else :
            cameraInfo = self.App.get_active_camerainfo()
            cameraPos = cameraInfo[3]
            tpinfoObj = self.get_tpinfo_obj(self.m_selectedTPInfo)
            tpinfoTextObj = self.get_tpinfo_text_obj(self.m_selectedTPInfo)

            self.__disconn_tpinfo_cl(self.m_selectedTPInfo)

            clickedPoint = self.App.picking_intersected_point(clickX, clickY, listExceptKeyType)
            if clickedPoint is not None :
                dist = algLinearMath.CScoMath.vec3_len(clickedPoint - cameraPos)
                self.m_ratio = dist / CComDragSelCLTP.s_pickingDepth
                # 이 부분에서 centerline도 감지 
                key = self.App.picking(clickX, clickY, listExceptKeyType)
                if key != "" and data.CData.get_type_from_key(key) == data.CData.s_skelTypeCenterline :
                    clID = data.CData.get_id_from_key(key)
                    self.__conn_tpinfo_cl(self.m_selectedTPInfo, clID)

            worldStart, pNearStart, pFarStart= self.App.get_world_from_mouse(clickX, clickY, CComDragSelCLTP.s_pickingDepth)
            dist = algLinearMath.CScoMath.vec3_len(worldStart - cameraPos)
            moveVec = cameraPos + (worldStart - cameraPos) * self.m_ratio
            self.m_selectedTPInfo.Pos = moveVec
            tpinfoObj.Pos = moveVec

            # tp text
            pos = tpinfoObj.Pos.copy()
            pos[0, 1] = pos[0, 1] + CComDragSelCLTP.s_tpRadius
            tpinfoTextObj.Pos = pos

        return True
    

    def command_reset_color(self) : 
        self.InputOPDragSelCL.process_reset()

        skeleton = self._get_skeleton()
        for tpinfo in self.m_listTPInfo :
            if tpinfo.TPKey in self.m_dicMatching.keys() :
                clID = self.m_dicMatching[tpinfo.TPKey]
                cl = skeleton.get_centerline(clID)
                self._set_clobj_color(cl, tpinfo.Color)
    def command_label_name(self, labelName : str) -> bool :
        if self.ready() == False :
            return False
        
        # selection clID 얻어옴
        # 해당 cl에 대해 labelName setting 
        listCLID = self.m_comDragFindCL.InputOPDragSelCL.get_all_selection_cl()
        if listCLID is None : 
            return False
        
        skeleton = self._get_skeleton()

        for clID in listCLID :
            cl = skeleton.get_centerline(clID)
            cl.Name = labelName

        self.refresh_cl_text()
        return True
    def command_labeling_descendant(self) -> bool : 
        if self.ready() == False :
            return False
        
        self.m_comDragFindCL.InputOPDragSelCL.process_reset()
        skeleton = self._get_skeleton()
        rootID = skeleton.RootCenterline.ID
        self.__labeling_descendant(rootID)

        self.refresh_cl_text()
        return True
    def command_visible_label(self, bVisible : bool) :
        if bVisible == True :
            self.App.ref_key_type(CComDragSelCLTP.s_tpVesselKeyType)
            self.App.ref_key_type_groupID(data.CData.s_textType, CComDragSelCLTP.s_tpLabelGroupID)
            self.App.ref_key_type_groupID(data.CData.s_textType, CComDragSelCLTP.s_textGroupID)
            self.command_reset_color()
        else :
            self.App.unref_key_type(CComDragSelCLTP.s_tpVesselKeyType)
            self.App.unref_key_type_groupID(data.CData.s_textType, CComDragSelCLTP.s_tpLabelGroupID)
            self.App.unref_key_type_groupID(data.CData.s_textType, CComDragSelCLTP.s_textGroupID)
            self._clear_clobj_color()
    

    # protected
    def _getui_lv_selected_tp(self) -> CTPInfo :
        selectedItems = self.InputUILVTP.selectedItems()
        if not selectedItems :
            return None
        
        item = selectedItems[0]
        text = item.text()
        node = item.data(Qt.UserRole) 
        return node
    def _getui_lv_find_tpinx(self, tpinfo : CTPInfo) -> int :
        count = self.InputUILVTP.count()
        for i in range(0, count) :
            item = self.InputUILVTP.item(i)
            node = item.data(Qt.UserRole)
            if node == tpinfo :
                return i
        return -1
    
    def _setui_lv_add_tp(self, tpinfo : CTPInfo) :
        self.InputUILVTP.blockSignals(True)

        name = tpinfo.Label
        item = QListWidgetItem(f"{name}")
        item.setData(Qt.UserRole, tpinfo)
        self.InputUILVTP.addItem(item)

        self.InputUILVTP.blockSignals(False)
    def _setui_lv_remove_tp(self, tpinfo : CTPInfo) :
        self.InputUILVTP.blockSignals(True)

        self.InputUILVTP.setCurrentItem(None)
        self.InputUILVTP.clearSelection()

        count = self.InputUILVTP.count()
        for i in reversed(range(count)):
            item = self.InputUILVTP.item(i)
            node = item.data(Qt.UserRole)
            if node == tpinfo :
                self.InputUILVTP.takeItem(i)
                del item
                break
        
        self.InputUILVTP.blockSignals(False)
    def _setui_lv_remove_all_tp(self) :
        self.InputUILVTP.clear()
    def _setui_lv_clear_selection_tp(self) :
        self.InputUILVTP.blockSignals(True)
        self.InputUILVTP.clearSelection()
        self.InputUILVTP.blockSignals(False)
    def _setui_lv_selection_tp(self, inx : int) :
        '''
        inx : 음수일 경우 selection을 해제 시킨다. 
        '''
        self.InputUILVTP.blockSignals(True)
        self.InputUILVTP.clearSelection()
        count = self.InputUILVTP.count()
        if 0 <= inx < count :
            self.InputUILVTP.setCurrentRow(inx)
        self.InputUILVTP.blockSignals(False)


    def _clear_clobj_color(self) :
        skeleton = self._get_skeleton()

        iCnt = skeleton.get_centerline_count()
        for inx in range(0, iCnt) :
            cl = skeleton.get_centerline(inx)
            self._set_clobj_color(cl)
    def _set_clobj_color(self, cl : algSkeletonGraph.CSkeletonCenterline, color = None) :
        datainst = self._get_data()
        clinfoInx = self._get_clinfoinx()
        clID = cl.ID

        if color is None :
            skeleton = self._get_skeleton()
            if clID == skeleton.RootCenterline.ID :
                color = data.CData.s_rootCLColor
            else :
                color = data.CData.s_clColor

        clKey = data.CData.make_key(data.CData.s_skelTypeCenterline, clinfoInx, clID)
        clObj = datainst.find_obj_by_key(clKey)
        clObj.Color = color

    
    # event
    def _on_lv_selection_tp(self, item) :
        node = item.data(Qt.UserRole)
        if node is None :
            print("not found node")
            return
        
        if self.m_selectedTPInfo is not None :
            tpinfoObj = self.get_tpinfo_obj(self.m_selectedTPInfo)
            tpinfoObj.Opacity = CComDragSelCLTP.s_tpOpacity
        self.m_selectedTPInfo = None

        self.m_selectedTPInfo = node
        tpinfoObj = self.get_tpinfo_obj(node)
        tpinfoObj.Opacity = 1.0

        self.App.update_viewer()

    
    # private
    # 여기에서 clObj에 대한 color도 갱신해줘야 함 
    def __attach_tpinfo_cl(self, tpinfo : CTPInfo) :
        skeleton = self._get_skeleton()

        self.__disconn_tpinfo_cl(tpinfo)

        cl = skeleton.find_nearest_centerline(tpinfo.Pos)
        if cl.ID not in self.m_dicMatching.values() :
            self.m_dicMatching[tpinfo.TPKey] = cl.ID
            cl.Name = tpinfo.Label
            self._set_clobj_color(cl, tpinfo.Color)
    def __conn_tpinfo_cl(self, tpinfo : CTPInfo, clID : int) :
        skeleton = self._get_skeleton()
        tpKey = tpinfo.TPKey

        self.__disconn_tpinfo_cl(tpinfo)
        
        cl = skeleton.get_centerline(clID)
        if cl.ID not in self.m_dicMatching.values() :
            self.m_dicMatching[tpinfo.TPKey] = cl.ID
            cl.Name = tpinfo.Label
            self._set_clobj_color(cl, tpinfo.Color)
    def __disconn_tpinfo_cl(self, tpinfo : CTPInfo) :
        skeleton = self._get_skeleton()
        tpKey = tpinfo.TPKey

        if tpinfo.TPKey in self.m_dicMatching.keys() :
            clID = self.m_dicMatching[tpKey]
            if clID >= 0 :
                cl = skeleton.get_centerline(clID)
                cl.Name = ""
                self._set_clobj_color(cl)
        self.m_dicMatching[tpKey] = -1
    def __labeling_descendant(self, clID : int) :
        skeleton = self._get_skeleton()
        cl = skeleton.get_centerline(clID)
        label = cl.Name

        parentID, listChildID = skeleton.get_conn_centerline_id(clID)
        for childID in listChildID :
            clChild = skeleton.get_centerline(childID)
            if clChild.Name == "" :
                clChild.Name = label
            self.__labeling_descendant(childID)
            

    @property
    def InputOPDragSelCL(self) -> operation.COperationDragSelectionCL :
        return self.m_comDragFindCL.InputOPDragSelCL
    @InputOPDragSelCL.setter
    def InputOPDragSelCL(self, opCL : operation.COperationDragSelectionCL) :
        self.m_comDragFindCL.InputOPDragSelCL = opCL
    @property
    def InputUILVTP(self) -> QListWidget :
        return self.m_inputUILVTP
    @InputUILVTP.setter
    def InputUILVTP(self, inputUILVTP : QListWidget) :
        self.m_inputUILVTP = inputUILVTP



class CComDragSkelCL(CComDrag) :
    def __init__(self, mediator) :
        '''
        desc 
            find dragged centerline 
        '''
        super().__init__(mediator)
        # input your code
        self.m_inputSkeleton = None
        self.m_inputSkelGroupID = -1
        self.m_opDragToggleCL = operation.COperationDragSelectionCLToggle(self.App)
        self.m_rt = None
        self.m_actorRt = self._create_rt_actor()
    def clear(self) :
        # input your code
        self.m_inputSkeleton = None
        self.m_inputSkelGroupID = -1
        self.m_opDragToggleCL = None
        super().clear()

    def ready(self) -> bool :
        if self.InputSkeleton is None :
            return False 
        if self.InputSkelGroupID == -1 :
            return False
        if self.m_opDragToggleCL is None : 
            return False
        return True
    def process_init(self) :
        if self.ready() == False :
            return False
        
        super().process_init()
        # input your code
        self.m_opDragToggleCL.Skeleton = self.InputSkeleton
    def process_end(self) :
        if self.ready() == False :
            return False
        
        self.m_opDragToggleCL.process_reset()
        # input your code
        super().process_end()
        
    def click(self, clickX : int, clickY : int, listExceptKeyType=None) -> bool :
        if self.ready() == False :
            return False
        
        super().click(clickX, clickY, listExceptKeyType)
        self.m_opDragToggleCL.process_reset()
        renderer = self._get_renderer()
        renderer.AddActor2D(self.m_actorRt)
        self._update_rt_actor()

        self.m_bDrag = True
        return True
    def click_with_shift(self, clickX : int, clickY : int, listExceptKeyType=None) -> bool :
        if self.ready() == False :
            return False
        
        super().click_with_shift(clickX, clickY, listExceptKeyType)
        renderer = self._get_renderer()
        renderer.AddActor2D(self.m_actorRt)
        self._update_rt_actor()

        self.m_bDrag = True
        return True
    def release(self, clickX : int, clickY : int) :
        if self.ready() == False :
            return False
        if self.Drag == False :
            return False

        renderer = self._get_renderer()
        renderer.RemoveActor2D(self.m_actorRt)

        listCLID = self._find_selection_clid()
        listKey = []
        if listCLID is not None :
            for clID in listCLID :
                pickingKey = data.CData.make_key(data.CData.s_skelTypeCenterline, self.InputSkelGroupID, clID)
                listKey.append(pickingKey)
            self.m_opDragToggleCL.add_toggle_selection_keys(listKey)
            self.m_opDragToggleCL.process()
        self.m_bDrag = False
        return True
    def move(self, clickX : int, clickY : int, listExceptKeyType=None) :
        if self.ready() == False :
            return
        if self.Drag == False :
            return False
        
        super().move(clickX, clickY, listExceptKeyType)
        self._update_rt_actor()
        return True

    def get_selection_clid(self) -> list :
        return self.m_opDragToggleCL.get_all_selection_cl()
    def get_selection_cl(self) -> list :
        retListCLID = self.get_selection_clid()
        skeleton = self.InputSkeleton
        return [skeleton.get_centerline(clid) for clid in retListCLID]
    
    def set_toggle_selection_clid(self, listCLID : list) :
        listKey = []
        for clid in listCLID :
            key = data.CData.make_key(data.CData.s_skelTypeCenterline, self.InputSkelGroupID, clid)
            listKey.append(key)

        self.m_opDragToggleCL.process_reset()
        if len(listKey) > 0 :
            childMode = self.m_opDragToggleCL.ChildSelectionMode
            self.m_opDragToggleCL.ChildSelectionMode = False
            self.m_opDragToggleCL.add_toggle_selection_keys(listKey)
            self.m_opDragToggleCL.process()
            self.m_opDragToggleCL.ChildSelectionMode = childMode
    

    # protected
    def _find_selection_clid(self) -> list :
        '''
        ret : [clID0, clID1, .. ]
        '''
        xmin, xmax = sorted([self.m_startX, self.m_endX])
        ymin, ymax = sorted([self.m_startY, self.m_endY])

        npPt = self.App.project_points_to_display(self.InputSkeleton.m_listKDTreeAnchor)
        inside = ((npPt[:,0] >= xmin) & (npPt[:,0] <= xmax) & (npPt[:,1] >= ymin) & (npPt[:,1] <= ymax))
        selectedIndex = np.where(inside)[0]

        listID = set()
        for inx in selectedIndex :
            listID.add(self.InputSkeleton.m_listKDTreeAnchorID[inx])
        
        listID = list(listID)
        if len(listID) == 0 :
            return None
        return listID
    def _create_rt_actor(self) :
        self.m_rt = vtk.vtkPoints()
        self.m_rt.SetNumberOfPoints(4)
        for i in range(4):
            self.m_rt.SetPoint(i, 0, 0, 0)

        rect_poly = vtk.vtkPolyData()
        rect_poly.SetPoints(self.m_rt)

        rect_cells = vtk.vtkCellArray()
        rect_cells.InsertNextCell(5)
        for i in [0, 1, 2, 3, 0]:
            rect_cells.InsertCellPoint(i)
        rect_poly.SetLines(rect_cells)

        mapper = vtk.vtkPolyDataMapper2D()
        mapper.SetInputData(rect_poly)

        actor = vtk.vtkActor2D()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(0.3, 1.0, 0.3)
        actor.GetProperty().SetLineWidth(2.0)
        return actor
    def _update_rt_actor(self) :
        x0 = self.m_startX
        y0 = self.m_startY
        x1 = self.m_endX
        y1 = self.m_endY
        self.m_rt.SetPoint(0, x0, y0, 0)
        self.m_rt.SetPoint(1, x1, y0, 0)
        self.m_rt.SetPoint(2, x1, y1, 0)
        self.m_rt.SetPoint(3, x0, y1, 0)
        self.m_rt.Modified()
    

    @property
    def InputSkeleton(self) -> algSkeletonGraph.CSkeleton :
        return self.m_inputSkeleton
    @InputSkeleton.setter
    def InputSkeleton(self, skeleton : algSkeletonGraph.CSkeleton) :
        self.m_inputSkeleton = skeleton
    @property
    def InputSkelGroupID(self) -> int :
        return self.m_inputSkelGroupID
    @InputSkelGroupID.setter
    def InputSkelGroupID(self, inputSkelGroupID : int) -> int :
        self.m_inputSkelGroupID = inputSkelGroupID

    @property
    def ChildSelectionMode(self) -> bool :
        return self.m_opDragToggleCL.ChildSelectionMode
    @ChildSelectionMode.setter
    def ChildSelectionMode(self, mode : bool) :
        self.m_opDragToggleCL.ChildSelectionMode = mode
    




if __name__ == '__main__' :
    pass


# print ("ok ..")

