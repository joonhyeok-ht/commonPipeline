import sys
import os
import numpy as np
import shutil
import vtk
import subprocess

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLineEdit, QLabel, QSizePolicy, QListWidget, QFileDialog, QFrame, QCheckBox, QTabWidget, QComboBox
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

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


import AlgUtil.algVTK as algVTK
import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algSkeletonGraph as algSkeletonGraph

import VtkObj.vtkObjLine as vtkObjLine
import VtkObj.vtkObjSphere as vtkObjSphere

import vtkObjGuideCL as vtkObjGuideCL

import data as data



class CSignal :
    def __init__(self) :
        self.m_listSignal = []
    def clear(self) :
        self.m_listSignal.clear()
    def process(self, *args, **kwargs) :
        for func in self.m_listSignal :
            func(*args, **kwargs)

    def add_slot(self, slot) :
        self.m_listSignal.append(slot)
    def get_slot_count(self) -> int :
        return len(self.m_listSignal)
    def get_slot(self, inx : int) :
        return self.m_listSignal[inx]
    def remove_slot_of_index(self, inx : int) :
        self.m_listSignal.pop(inx)
    def remove_slot(self, slot) :
        if slot in self.m_listSignal :
            self.m_listSignal.remove(slot)
    def is_slot(self, slot) -> bool :
        if slot in self.m_listSignal :
            return True
        return False 



if __name__ == '__main__' :
    pass


# print ("ok ..")

