"""FLOWPanel controls with isolated, asynchronous worker processes."""
import json
import os
import shutil
import sys
import tomllib
import time
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QProcess, QProcessEnvironment, QTimer
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QLabel, QComboBox, QDoubleSpinBox, QLineEdit, QFileDialog,
    QMessageBox, QPlainTextEdit, QTabWidget, QGroupBox, QProgressBar, QScrollArea)
from core.flowpanel_workflow import ROOT, read_case, configure_run, is_weber_case, solver_script, validate_weber_document


class FlowPanelPanel(QWidget):
    def __init__(self, application, parent=None):
        super().__init__(parent)
        self.application = application
        self.case = None
        self.viewer = None
        self.plots = None
        self.pending = None
        self.task_log_path = None
        self.started_at = 0
        self.layout_kind = None
        self.task_timer = QTimer(self)
        self.task_timer.setInterval(1000)
        self.task_timer.timeout.connect(self.update_task_status)
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.setWorkingDirectory(str(ROOT))
        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONUNBUFFERED", "1")
        env.insert("PYTHONIOENCODING", "utf-8")
        self.process.setProcessEnvironment(env)
        self.process.readyReadStandardOutput.connect(self.read_output)
        self.process.finished.connect(self.finished)
        self.process.errorOccurred.connect(self.process_error)
        layout = QVBoxLayout(self)
        note = QLabel("FLOWPanel analysis — Manta aircraft or isolated Weber wing. "
                      "Apply model edits before preparing a mesh.")
        self.layout_note = note
        note.setWordWrap(True)
        layout.addWidget(note)
        self.case_label = QLabel("No mesh case selected")
        self.case_label.setWordWrap(True)
        layout.addWidget(self.case_label)
        self.controls = QGroupBox("Mesh and simulation settings")
        form = QFormLayout(self.controls)
        self.mode = QComboBox()
        self.mode.addItem("Complete aircraft", "aircraft")
        self.mode.addItem("Wing only", "wing")
        self.level = QComboBox()
        for label, value in (("Coarse", "coarse"), ("Medium", "medium"), ("Fine (mesh review only)", "fine")):
            self.level.addItem(label, value)
        form.addRow("Geometry", self.mode)
        form.addRow("Resolution", self.level)
        self.speed = self.number(0.01, 1000, 20)
        self.alpha = self.number(-30, 30, 4)
        self.density = self.number(.001, 100, 1.225, 4)
        form.addRow("Speed (m/s)", self.speed)
        form.addRow("Angle of attack (deg)", self.alpha)
        form.addRow("Density (kg/m³)", self.density)
        default = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/Julia/julia-1.11.9/bin/julia.exe"
        self.julia = QLineEdit(shutil.which("julia") or (str(default) if default.is_file() else ""))
        browse = QPushButton("Browse…")
        browse.clicked.connect(self.choose_julia)
        row = QHBoxLayout()
        row.addWidget(self.julia)
        row.addWidget(browse)
        form.addRow("Julia executable", row)
        layout.addWidget(self.controls)
        buttons = QHBoxLayout()
        self.prepare_button = QPushButton("Prepare mesh")
        self.open_button = QPushButton("Open case")
        self.configure_button = QPushButton("Configure simulation")
        self.run_button = QPushButton("Run simulation")
        self.mesh_button = QPushButton("View mesh")
        self.result_button = QPushButton("View results")
        self.plots_button = QPushButton('View plots')
        self.cancel_button = QPushButton("Cancel task")
        for button, callback in ((self.prepare_button, self.prepare), (self.open_button, self.open_case),
                                 (self.configure_button, self.configure),
                                 (self.run_button, self.run), (self.mesh_button, self.view_mesh),
                                 (self.result_button, self.view_results), (self.plots_button, self.view_plots),
                                 (self.cancel_button, self.cancel)):
            buttons.addWidget(button)
            button.clicked.connect(callback)
        layout.addLayout(buttons)
        self.task_status = QLabel("Ready. A simulation computes a steady result, not an animation.")
        self.task_status.setWordWrap(True)
        layout.addWidget(self.task_status)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        self.summary = QLabel("Results are preliminary until mesh convergence is checked. Inviscid drag excludes friction.")
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        self.tabs = QTabWidget()
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(3000)
        self.tabs.addTab(self.log, "Task log")
        # Keep setup in its own page so results retain the full working height.
        layout.removeWidget(note)
        layout.removeWidget(self.controls)
        setup = QWidget()
        setup_layout = QVBoxLayout(setup)
        setup_layout.addWidget(note)
        setup_layout.addWidget(self.controls)
        setup_layout.addStretch()
        self.setup_page = QScrollArea()
        self.setup_page.setWidgetResizable(True)
        self.setup_page.setWidget(setup)
        self.tabs.insertTab(0, self.setup_page, 'Simulation setup')
        self.tabs.setCurrentWidget(self.setup_page)
        layout.addWidget(self.tabs, 1)
        self.set_busy(False)

    def refresh_layout(self):
        if self.busy():
            return
        types = sorted(o.tipo for o in self.application.documento.objetos)
        kind = 'weber' if types == ['Ala'] else 'manta' if types == ['Ala', 'Fuselaje'] else 'unsupported'
        if kind != self.layout_kind:
            self.layout_kind = kind
            if self.case is None:
                self.speed.setValue(30 if kind == 'weber' else 20)
                self.alpha.setValue(4.2 if kind == 'weber' else 4)
                if kind == 'manta':
                    self.mode.setCurrentIndex(self.mode.findData('aircraft'))
        self.mode.setEnabled(kind != 'weber')
        if kind == 'weber':
            self.mode.setCurrentIndex(self.mode.findData('wing'))
            self.layout_note.setText('FLOWPanel analysis — isolated Weber wing\n'
                'Supported: RAE101, span 2489.2 mm, constant chord 497.84 mm, sweep 45°, '
                'no twist, dihedral or placement rotation/translation. Open-tip analysis mesh. '
                'Defaults: 30 m/s, 4.2°. Other wing geometries are not supported by this adapter.')
        else:
            self.layout_note.setText('FLOWPanel analysis — Manta layout\n'
                'Supported: one symmetric, unrotated wing and one center body. '
                'An isolated Weber wing is also supported. Apply model edits before preparing a mesh.')
        self.level.setItemText(2, 'Fine (31,104 panels; memory intensive)' if kind == 'weber' else 'Fine (mesh review only)')

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_layout()

    def document_changed(self):
        if self.busy():
            return
        self.case = None
        self.layout_kind = None
        self.case_label.setText('No mesh case selected. Prepare a mesh or open an existing case.')
        self.summary.setText('Model loaded. Prepare a new mesh after applying geometry edits.')
        self.tabs.setCurrentWidget(self.log)
        if self.viewer is not None:
            self.tabs.setTabEnabled(self.tabs.indexOf(self.viewer), False)
        if self.plots is not None:
            self.tabs.setTabEnabled(self.tabs.indexOf(self.plots), False)
        self.refresh_layout()
        self.set_busy(False)

    @staticmethod
    def number(low, high, value, decimals=2):
        widget = QDoubleSpinBox()
        widget.setDecimals(decimals)
        widget.setRange(low, high)
        widget.setValue(value)
        return widget

    def error(self, error):
        QMessageBox.critical(self, "Analysis", str(error))

    def choose_julia(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Select Julia executable")
        if filename:
            self.julia.setText(filename)

    def busy(self):
        return self.process.state() != QProcess.ProcessState.NotRunning

    def set_busy(self, busy):
        self.controls.setEnabled(not busy)
        for button in (self.prepare_button, self.open_button, self.configure_button):
            button.setEnabled(not busy)
        for button in (self.run_button, self.mesh_button, self.result_button):
            button.setEnabled(not busy and self.case is not None)
        self.cancel_button.setEnabled(busy)
        self.cancel_button.setVisible(busy)
        self.plots_button.setEnabled(not busy and self.case is not None)
        if not busy:
            self.refresh_layout()

    def start(self, executable, arguments, done):
        logs = ROOT / "exports/flowpanel/logs"
        try:
            logs.mkdir(parents=True, exist_ok=True)
            self.task_log_path = logs / (uuid4().hex + ".log")
            self.task_log_path.write_text("Starting: " + executable + " " + " ".join(arguments) + "\n", encoding="utf-8")
        except OSError as error:
            self.error(f"Unable to create task log: {error}")
            return
        self.pending = done
        self.started_at = time.monotonic()
        self.progress.setVisible(True)
        self.task_timer.start()
        self.update_task_status()
        self.set_busy(True)
        self.tabs.setCurrentWidget(self.log)
        self.log.appendPlainText("Starting: " + executable + " " + " ".join(arguments))
        self.process.start(executable, arguments)

    def read_output(self):
        text = bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="replace")
        self.log.moveCursor(QTextCursor.MoveOperation.End)
        self.log.insertPlainText(text)
        if self.task_log_path:
            try:
                with self.task_log_path.open("a", encoding="utf-8") as stream:
                    stream.write(text)
            except OSError:
                pass  # Keep displaying process output even if disk logging fails.

    def update_task_status(self):
        elapsed = int(time.monotonic() - self.started_at)
        self.task_status.setText(f"Task in progress — {elapsed}s. Startup may take a few minutes. See Task log for details.")

    def stop_task_status(self, message):
        self.task_timer.stop()
        self.progress.setVisible(False)
        self.task_status.setText(message)
        self.task_status.setToolTip(str(self.task_log_path or ''))

    def process_error(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            self.pending = None
            self.set_busy(False)
            self.stop_task_status("Unable to start: " + self.process.errorString())
            self.error(self.process.errorString())

    def finished(self, code, status):
        self.read_output()
        callback, self.pending = self.pending, None
        self.set_busy(False)
        if callback is None:
            self.stop_task_status("Task stopped without completing new results.")
            return
        if code != 0 or status != QProcess.ExitStatus.NormalExit:
            self.stop_task_status(f"Task failed (exit code {code}). Open Task log for the error.")
            self.error("Task failed. See the task log. Previous cases and results were preserved.")
            return
        try:
            self.stop_task_status("Calculation finished. Loading output…")
            callback()
            self.task_status.setText(self.task_status.text().replace("Calculation finished. Loading output…", "Task complete."))
        except Exception as error:
            self.stop_task_status("Unable to load task output: " + str(error))
            self.error(error)

    def cancel(self):
        self.pending = None
        self.process.kill()
        self.log.appendPlainText("Task cancelled; incomplete output must not be used as results.")

    def prepare(self):
        try:
            self.refresh_layout()
            objects = self.application.documento.objetos
            types = sorted(o.tipo for o in objects)
            if types not in (["Ala", "Fuselaje"], ["Ala"]):
                raise ValueError("Supported layouts: the isolated Weber wing, or the Manta wing and center body.")
            document = {"formato": "WingCAD", "version": 1,
                "documento": {"nombre": self.application.documento.nombre,
                "objetos": [self.application._serializar_objeto(o) for o in objects]}}
            if types == ['Ala']:
                validate_weber_document(document)
            folder = ROOT / "exports/flowpanel/gui" / uuid4().hex
            folder.mkdir(parents=True)
            source = folder / "source.wingcad"
            # Serialize without marking the user's document as saved.
            source.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
            mode, level = self.mode.currentData(), self.level.currentData()
            if types == ['Ala']:
                counts = {'coarse': (48,16), 'medium': (72,24), 'fine': (108,36)}
                nc, ns = counts[level]
                case = folder / 'weber' / level
                self.start(sys.executable, [str(ROOT/'analysis/flowpanel/sweptwing/prepare_ordered.py'),
                    '--source', str(source), '--output', str(folder/'weber'), '--connected',
                    '--triangulation', 'mirrored_shortest', '--spacing', 'bounded',
                    '--resolutions', f'{level}:{nc}:{ns}'], lambda: self.select_case(case))
                return
            case = folder / mode / level
            self.start(sys.executable, [str(ROOT / "analysis/flowpanel/prepare.py"),
                "--source", str(source), "--output", str(folder), "--mode", mode, "--level", level],
                lambda: self.select_case(case))
        except Exception as error:
            self.error(error)

    def select_case(self, folder):
        data = read_case(folder)
        self.case = Path(folder)
        if self.plots is not None:
            self.tabs.setTabEnabled(self.tabs.indexOf(self.plots), False)
            if self.tabs.currentWidget() is self.plots:
                self.tabs.setCurrentWidget(self.setup_page)
        moment = f"; moment reference: {data['moment_reference_m']} m" if 'moment_reference_m' in data else ''
        adapter = 'Weber wing' if is_weber_case(data) else 'Manta'
        self.case_label.setText(f"{adapter}  ·  {data['panels']:,} panels  ·  Reference area {data['sref_m2']:.3f} m²")
        self.case_label.setToolTip(f"Case: {folder}{moment}")
        self.speed.setValue(data["speed_mps"])
        self.alpha.setValue(data["aoa_deg"])
        self.density.setValue(data["density_kg_m3"])
        self.summary.setText("Mesh case loaded. Run results are saved separately; editing the CAD model does not update this mesh.")
        self.set_busy(False)

    def configure(self):
        self.controls.setVisible(True)
        self.tabs.setCurrentWidget(self.setup_page)
        self.speed.setFocus()
        self.speed.selectAll()

    def open_case(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Open mesh or simulation case", str(ROOT / "exports/flowpanel"), "Case (case.toml)")
        if filename:
            try:
                self.select_case(Path(filename).parent)
            except Exception as error:
                self.error(error)

    def run(self):
        try:
            executable = self.julia.text().strip()
            if not Path(executable).is_file():
                raise ValueError("Select an installed Julia executable first.")
            run = configure_run(self.case, self.speed.value(), self.alpha.value(), self.density.value())
            self.start(executable, ["--startup-file=no", "--project=" + str(ROOT / "analysis/flowpanel"),
                str(solver_script(read_case(run))), str(run)], lambda: self.run_complete(run))
        except Exception as error:
            self.error(error)

    def run_complete(self, folder):
        self.select_case(folder)
        self.view_results()

    def view_mesh(self):
        folder = self.case
        self.start(sys.executable, [str(ROOT / "analysis/flowpanel/view_mesh.py"), str(folder)],
                   lambda: self.show_file(folder / "surface.vtk", False))

    def show_file(self, path, pressure):
        if self.viewer is None:
            from gui.analysis_view import AnalysisView
            self.viewer = AnalysisView(self)
            self.tabs.addTab(self.viewer, "Analysis 3D")
        self.viewer.load(path, pressure)
        self.tabs.setTabEnabled(self.tabs.indexOf(self.viewer), True)
        self.tabs.setCurrentWidget(self.viewer)

    def view_results(self):
        try:
            folder = self.case / "results"
            data = tomllib.loads((folder / "coefficients.toml").read_text(encoding="utf-8"))
            self.show_file(folder / ('wing_C.vtk' if is_weber_case(read_case(self.case)) else 'manta.vtk'), True)
            moment = f"    Cm: {data['Cm']:.5f}" if 'Cm' in data else ''
            self.summary.setText(f"CL: {data['CL']:.5f}    CD (inviscid): {data['CD_inviscid']:.5f}    "
                f"{moment}    Cp: {data['Cp_min']:.3f} to {data['Cp_max']:.3f}")
        except FileNotFoundError:
            self.error("No completed results for this case. Run a simulation or open an existing run's case.toml.")
        except Exception as error:
            self.error(error)

    def view_plots(self):
        try:
            if not is_weber_case(read_case(self.case)):
                raise ValueError('Section plots currently support the isolated Weber wing.')
            if not (self.case/'results/coefficients.toml').is_file():
                raise ValueError('Run a simulation or open a completed run first.')
            case=self.case
            self.start(sys.executable,[str(ROOT/'analysis/flowpanel/plot_run.py'),str(case)],
                       lambda: self.show_plots(case/'results/plots'))
        except Exception as error:
            self.error(error)

    def show_plots(self,folder):
        if self.plots is None:
            from gui.analysis_plots import AnalysisPlots
            self.plots=AnalysisPlots(self)
            self.tabs.addTab(self.plots,'Plots')
        self.plots.load(folder)
        self.tabs.setTabEnabled(self.tabs.indexOf(self.plots),True)
        self.tabs.setCurrentWidget(self.plots)

    def finalize(self):
        if self.viewer:
            self.viewer.finalize()
