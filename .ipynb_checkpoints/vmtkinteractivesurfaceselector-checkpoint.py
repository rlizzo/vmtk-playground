from __future__ import absolute_import #NEEDS TO STAY AS TOP LEVEL MODULE FOR Py2-3 COMPATIBILITY
import vtk
import sys
import numpy as np
import copy

from vmtk import vtkvmtk
from vmtk import vmtkrenderer
from vmtk import pypes


class vmtkSeedSelector(object):
    def __init__(self):
        self._Surface = None
        self._SeedIds = None
        self._TargetSeedIds = vtk.vtkFloatArray()
        self.PrintError = None
        self.PrintLog = None
        self.InputText = None
        self.OutputText = None
        self.InputInfo = None
        self.PickedScalarData = None
        self._OutputSeedIds = []

    def SetSurface(self, surface):
        self._Surface = surface

    def GetSurface(self):
        return self._Surface

    def GetTargetSeedIds(self):
        return self._TargetSeedIds
    
    def GetOutputSeedIds(self):
        return self._OutputSeedIds

    def Execute(self):
        pass

class vmtkPickPointSeedSelector(vmtkSeedSelector):

    def __init__(self):
        vmtkSeedSelector.__init__(self)
        self.PickedSeedIds = vtk.vtkIdList()
        self.PickedSeeds = vtk.vtkPolyData()
        self.vmtkRenderer = None
        self.OwnRenderer = 0
        self.Script = None
        

    def UndoCallback(self, obj):
        self.InitializeSeeds()
        self.PickedSeeds.Modified()
        self.vmtkRenderer.RenderWindow.Render()
        self._OutputSeedIds.pop()
        self.PickedActor.GetProperty().SetColor(np.random.random(1), 
                                                np.random.random(1),
                                                np.random.random(1))
        self.PickedActor.GetProperty().SetDiffuse(1.0)
        self.PickedActor.GetProperty().SetSpecular(0.0)
        
        return

    def PickCallback(self, obj):
        picker = vtk.vtkPropPicker()
        eventPosition = self.vmtkRenderer.RenderWindowInteractor.GetEventPosition()
        result = picker.Pick(float(eventPosition[0]),float(eventPosition[1]),0.0,self.vmtkRenderer.Renderer)
        if result is None:
            return
        elif result == 0:
            return
        self.PickedActor = picker.GetActor()
        
        self.PickedActor.GetProperty().SetColor(1.0, 0.0, 0.0)
        self.PickedActor.GetProperty().SetDiffuse(1.0)
        self.PickedActor.GetProperty().SetSpecular(0.0)
        
        self.PickedPoly = self.PickedActor.GetMapper().GetInputAsDataSet()
        self.PickedScalarData = self.PickedPoly.GetPointData().GetScalars()
        
        self._OutputSeedIds.append(copy.deepcopy(self.PickedScalarData.GetValue(0)))
        
        return

        
    def InitializeSeeds(self):
        self.PickedSeedIds.Initialize()
        self.PickedSeeds.Initialize()
        seedPoints = vtk.vtkPoints()
        self.PickedSeeds.SetPoints(seedPoints)

    def Execute(self):

        if (self._Surface == None):
            self.PrintError('vmtkPickPointSeedSelector Error: Surface not set.')
            return

        self._TargetSeedIds.Initialize()

        if not self.vmtkRenderer:
            self.vmtkRenderer = vmtkrenderer.vmtkRenderer()
            self.vmtkRenderer.Initialize()
            self.OwnRenderer = 1

        self.vmtkRenderer.RegisterScript(self.Script)

        ##self.vmtkRenderer.RenderWindowInteractor.AddObserver("KeyPressEvent", self.KeyPressed)
        self.vmtkRenderer.AddKeyBinding('u','Undo.',self.UndoCallback)
        self.vmtkRenderer.AddKeyBinding('space','Add points.',self.PickCallback)

        self.InputInfo('Please position the mouse and press space to add target points, \'u\' to undo\n')

        any = 0
        while any == 0:
            self.InitializeSeeds()
            self.vmtkRenderer.Render()
            try:
                any = self.PickedScalarData.GetValue(0)
            except AttributeError:
                any = None
        if self.OwnRenderer:
            self.vmtkRenderer.Deallocate()


class vmtkInteractiveSelector(pypes.pypeScript):
    def __init__(self):

        pypes.pypeScript.__init__(self)

        self.SeedSelector = None
        self.Surface = None
        self.vmtkRenderer = None
        self.OwnRenderer = 0
        self.OutputSeedIds = []

        self.SetScriptName('vmtkInteractiveSelector')
        self.SetScriptDoc('')
        self.SetInputMembers([
            ['Surface', 'i', 'vtkPolyData', 1, '', 'the input surface', 'vmtksurfacereader'],
            ['vmtkRenderer', 'renderer', 'vmtkRenderer', 1, '', 'external renderer']])
        self.SetOutputMembers([
            ['OutputSeedIds','o','vtkFloatArray',1,'','the output seed ids', '']])

    def Execute(self):

        if self.Surface == None:
            self.PrintError('Error: No input surface.')

        if self.vmtkRenderer is None:
            self.vmtkRenderer = vmtkrenderer.vmtkRenderer()
            self.vmtkRenderer.Initialize()
            self.vmtkRenderer.Renderer.SetBackground(.1, .1, .2 )
            self.OwnRenderer = 1
            
        if self.SeedSelector:
            pass
        else:
            self.SeedSelector = vmtkPickPointSeedSelector()
            self.SeedSelector.vmtkRenderer = self.vmtkRenderer
            self.SeedSelector.Script = self
        
        connectiv = vtk.vtkPolyDataConnectivityFilter()
        connectiv.SetInputData(self.Surface)
        connectiv.SetExtractionModeToAllRegions()
        connectiv.ColorRegionsOn()
        connectiv.Update()
        numRegions = connectiv.GetNumberOfExtractedRegions()
        print(numRegions)

        for surfaceId in range(numRegions):
            connectiv2 = vtk.vtkPolyDataConnectivityFilter()
            connectiv2.SetExtractionModeToSpecifiedRegions()
            connectiv2.SetInputData(connectiv.GetOutput())
            connectiv2.AddSpecifiedRegion(surfaceId)
            connectiv2.Update()
            print(connectiv.GetNumberOfExtractedRegions())
            surf = connectiv2.GetOutput()
            
            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputData(surf)
            mapper.ScalarVisibilityOff()
            actor = vtk.vtkActor()
            actor.SetMapper(mapper)

            r = np.random.randint(20, high=70) / 100.0
            g = np.random.randint(20, high=70) / 100.0
            b = np.random.randint(20, high=70) / 100.0
            actor.GetProperty().SetColor(r, g, b)
            actor.GetProperty().SetDiffuse(1.0)
            actor.GetProperty().SetSpecular(0.2)
            actor.GetProperty().SetRepresentationToSurface()
            actor.GetProperty().EdgeVisibilityOff()

            self.vmtkRenderer.Renderer.AddActor(actor)
            

        if self.SeedSelector:
            self.SeedSelector.SetSurface(self.Surface)
            self.SeedSelector.InputInfo = self.InputInfo
            self.SeedSelector.InputText = self.InputText
            self.SeedSelector.OutputText = self.OutputText
            self.SeedSelector.PrintError = self.PrintError
            self.SeedSelector.PrintLog = self.PrintLog
            self.SeedSelector.Execute()

            self.OutputSeedIds.append(self.SeedSelector.GetOutputSeedIds())

        if self.OwnRenderer:
            self.vmtkRenderer.Deallocate()


if __name__ == '__main__':
    main = pypes.pypeMain()
    main.Arguments = sys.argv
    main.Execute()