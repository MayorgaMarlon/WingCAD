"""Lazy, interactive analysis viewer. Construct only inside the running app."""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QCheckBox


class AnalysisView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        import vtk
        from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
        self.vtk = vtk
        layout = QVBoxLayout(self)
        bar = QHBoxLayout()
        fit = QPushButton("Fit view")
        self.edges = QCheckBox("Mesh edges")
        self.edges.setChecked(True)
        self.wake = QCheckBox("Show wake")
        self.range = QCheckBox("Cp display range: -1.2 to 1 (clipped colors)")
        for control in (fit, self.edges, self.wake, self.range):
            bar.addWidget(control)
        layout.addLayout(bar)
        self.widget = QVTKRenderWindowInteractor(self)
        layout.addWidget(self.widget)
        self.renderer = vtk.vtkRenderer()
        self.renderer.SetBackground(.12, .15, .20)
        self.widget.GetRenderWindow().AddRenderer(self.renderer)
        self.widget.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera())
        self.widget.Initialize()
        self.actor = None
        self.wake_actor = None
        fit.clicked.connect(self.fit)
        self.edges.toggled.connect(self.update_display)
        self.wake.toggled.connect(self.update_display)
        self.range.toggled.connect(self.update_display)

    def load(self, path, pressure=False):
        vtk = self.vtk
        reader = vtk.vtkUnstructuredGridReader()
        reader.SetFileName(str(path))
        reader.ReadAllScalarsOn()
        reader.Update()
        grid = reader.GetOutput()
        if grid.GetNumberOfCells() == 0:
            raise ValueError("The analysis file contains no cells.")
        cp = grid.GetCellData().GetArray("Cp")
        if pressure and cp is None:
            raise ValueError("The result does not contain Cp.")
        self.renderer.RemoveAllViewProps()
        self.mapper = vtk.vtkDataSetMapper()
        self.mapper.SetInputData(grid)
        self.actor = vtk.vtkActor()
        self.actor.SetMapper(self.mapper)
        self.actor.GetProperty().SetColor(.65, .8, .92)
        self.actor.GetProperty().SetEdgeColor(.2, .25, .3)
        self.renderer.AddActor(self.actor)
        self.pressure = pressure
        self.range.setEnabled(pressure)
        if pressure:
            self.full_range = cp.GetRange()
            self.mapper.SetScalarModeToUseCellFieldData()
            self.mapper.SelectColorArray("Cp")
            lut = vtk.vtkLookupTable()
            lut.SetHueRange(.667, 0)
            lut.Build()
            self.mapper.SetLookupTable(lut)
            scale = vtk.vtkScalarBarActor()
            scale.SetLookupTable(lut)
            scale.SetTitle("Cp")
            scale.SetNumberOfLabels(6)
            self.renderer.AddActor2D(scale)
        else:
            self.mapper.ScalarVisibilityOff()
        self.wake_actor = None
        wake_path = path.parent / "manta_wake.vtk"
        if pressure and wake_path.is_file():
            wake_reader = vtk.vtkUnstructuredGridReader()
            wake_reader.SetFileName(str(wake_path))
            wake_reader.Update()
            mapper = vtk.vtkDataSetMapper()
            mapper.SetInputData(wake_reader.GetOutput())
            mapper.ScalarVisibilityOff()
            self.wake_actor = vtk.vtkActor()
            self.wake_actor.SetMapper(mapper)
            self.wake_actor.GetProperty().SetColor(.85, .85, .85)
            self.wake_actor.GetProperty().SetRepresentationToWireframe()
            self.renderer.AddActor(self.wake_actor)
        self.wake.setEnabled(self.wake_actor is not None)
        self.update_display()
        self.fit()

    def update_display(self):
        if self.actor is None:
            return
        self.actor.GetProperty().SetEdgeVisibility(self.edges.isChecked())
        if self.pressure:
            self.mapper.SetScalarRange(*((-1.2, 1) if self.range.isChecked() else self.full_range))
        if self.wake_actor:
            self.wake_actor.SetVisibility(self.wake.isChecked())
        self.widget.GetRenderWindow().Render()

    def fit(self):
        self.renderer.ResetCamera()
        self.widget.GetRenderWindow().Render()

    def finalize(self):
        self.widget.Finalize()
