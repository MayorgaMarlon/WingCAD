"""Lazy, interactive analysis viewer. Construct only inside the running app."""
import csv
import tomllib
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QCheckBox,
    QSplitter, QTabWidget, QTableWidget, QTableWidgetItem, QAbstractItemView,
    QHeaderView, QLabel, QFileDialog, QMessageBox)
from core.analysis_results import result_tables, display_value


class AnalysisView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        import vtk
        from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
        self.vtk = vtk
        layout = QVBoxLayout(self)
        bar = QHBoxLayout()
        fit = QPushButton("Fit view")
        fit.setMaximumWidth(100)
        self.edges = QCheckBox("Mesh edges")
        self.edges.setChecked(True)
        self.wake = QCheckBox("Show wake")
        self.range = QCheckBox("Limit Cp colors")
        self.range.setToolTip('Display colors from -1.2 to 1. Values outside this range are saturated; saved results stay unchanged.')
        for control in (fit, self.edges, self.wake, self.range):
            bar.addWidget(control)
        bar.addStretch()
        layout.addLayout(bar)
        self.splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.widget = QVTKRenderWindowInteractor(self)
        self.widget.setMinimumSize(320, 300)
        self.splitter.addWidget(self.widget)
        self.details = QWidget(self)
        self.details.setMinimumWidth(330)
        self.details.setMaximumWidth(560)
        self.splitter.setChildrenCollapsible(False)
        details_layout = QVBoxLayout(self.details)
        self.result_source = QLabel()
        self.result_source.setWordWrap(True)
        self.result_source.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        details_layout.addWidget(self.result_source)
        self.tables = QTabWidget()
        self.result_table = self.make_table()
        self.condition_table = self.make_table()
        self.tables.addTab(self.result_table, 'Results')
        self.tables.addTab(self.condition_table, 'Run conditions')
        details_layout.addWidget(self.tables, 1)
        note = QLabel('Preliminary · convergence not established.\nInviscid drag excludes skin friction.')
        note.setWordWrap(True)
        details_layout.addWidget(note)
        export = QPushButton('Export tables to CSV')
        export.clicked.connect(self.export_tables)
        details_layout.addWidget(export)
        self.splitter.addWidget(self.details)
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 2)
        self.splitter.setSizes([750, 430])
        layout.addWidget(self.splitter)
        self.details.hide()
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

    @staticmethod
    def make_table():
        table = QTableWidget(0, 3)
        table.setHorizontalHeaderLabels(['Quantity', 'Value', 'Unit'])
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.verticalHeader().hide()
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        return table

    def load_tables(self, path):
        data = tomllib.loads(path.with_name('coefficients.toml').read_text(encoding='utf-8'))
        self.saved_rows = result_tables(data)
        self.saved_result_path = path
        self.result_source.setText(f"Saved results · {data.get('level', 'mesh')} · {data.get('panels', '—'):,} panels"
                                  if isinstance(data.get('panels'), int) else 'Saved results')
        self.result_source.setToolTip(str(path.parent.parent))
        for table, rows in zip((self.result_table, self.condition_table), self.saved_rows):
            table.setRowCount(len(rows))
            for row, values in enumerate(rows):
                for col, value in enumerate(values):
                    item = QTableWidgetItem(display_value(value))
                    item.setToolTip(str(value))
                    table.setItem(row, col, item)
            table.resizeRowsToContents()

    def export_tables(self):
        filename, _ = QFileDialog.getSaveFileName(self, 'Export saved results',
            str(self.saved_result_path.parent/'results_table.csv'), 'CSV (*.csv)')
        if not filename:
            return
        try:
            with open(filename, 'w', newline='', encoding='utf-8-sig') as stream:
                writer = csv.writer(stream)
                writer.writerow(['Section', 'Quantity', 'Value', 'Unit'])
                for section, rows in zip(('Results', 'Run conditions'), self.saved_rows):
                    writer.writerows((section, *row) for row in rows)
        except OSError as error:
            QMessageBox.critical(self, 'Export failed', str(error))

    def load(self, path, pressure=False):
        self.details.hide()
        if pressure:
            self.load_tables(path)
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
            scale.SetPosition(.87, .12)
            scale.SetWidth(.11)
            scale.SetHeight(.70)
            scale.UnconstrainedFontSizeOn()
            scale.GetTitleTextProperty().SetFontSize(18)
            scale.GetLabelTextProperty().SetFontSize(12)
            self.renderer.AddActor2D(scale)
        else:
            self.mapper.ScalarVisibilityOff()
        self.wake_actor = None
        wake_path = path.with_name(path.stem + "_wake.vtk")
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
        self.details.setVisible(pressure)
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
