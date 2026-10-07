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
    QMessageBox, QPlainTextEdit, QTabWidget, QGroupBox, QProgressBar)
from core.flowpanel_workflow import ROOT, read_case, configure_run


class FlowPanelPanel(QWidget):
    def __init__(self, application, parent=None):
        super().__init__(parent)
        self.application = application
        self.case = None
        self.viewer = None
        self.pending = None
        self.task_log_path = None
        self.started_at = 0
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
        note = QLabel("FLOWPanel analysis — Manta layout\n"
                      "Supported: one symmetric, unrotated wing and one center body. "
                      "Other aircraft layouts need a dedicated mesh adapter. "
                      "Apply model edits before preparing a mesh.")
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
        self.cancel_button = QPushButton("Cancel task")
        for button, callback in ((self.prepare_button, self.prepare), (self.open_button, self.open_case),
                                 (self.configure_button, self.configure),
                                 (self.run_button, self.run), (self.mesh_button, self.view_mesh),
                                 (self.result_button, self.view_results), (self.cancel_button, self.cancel)):
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
        layout.addWidget(self.tabs, 1)
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
        self.task_status.setText(message + (f"\nLog: {self.task_log_path}" if self.task_log_path else ""))

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
            objects = self.application.documento.objetos
            if sorted(o.tipo for o in objects) != ["Ala", "Fuselaje"]:
                raise ValueError("Open the Manta example first. This adapter requires one wing and one center body.")
            folder = ROOT / "exports/flowpanel/gui" / uuid4().hex
            folder.mkdir(parents=True)
            source = folder / "source.wingcad"
            # Serialize without marking the user's document as saved.
            source.write_text(json.dumps({"formato": "WingCAD", "version": 1,
                "documento": {"nombre": self.application.documento.nombre,
                "objetos": [self.application._serializar_objeto(o) for o in objects]}}, ensure_ascii=False), encoding="utf-8")
            mode, level = self.mode.currentData(), self.level.currentData()
            case = folder / mode / level
            self.start(sys.executable, [str(ROOT / "analysis/flowpanel/prepare.py"),
                "--source", str(source), "--output", str(folder), "--mode", mode, "--level", level],
                lambda: self.select_case(case))
        except Exception as error:
            self.error(error)

    def select_case(self, folder):
        data = read_case(folder)
        self.case = Path(folder)
        self.case_label.setText(f"Case: {folder}\n{data['panels']:,} panels; reference area: {data['sref_m2']:.3f} m²; "
                               f"moment reference: {data['moment_reference_m']} m.\nSettings below apply to the next run.")
        self.speed.setValue(data["speed_mps"])
        self.alpha.setValue(data["aoa_deg"])
        self.density.setValue(data["density_kg_m3"])
        self.summary.setText("Mesh case loaded. Run results are saved separately; editing the CAD model does not update this mesh.")
        self.set_busy(False)

    def configure(self):
        self.controls.setVisible(True)
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
                str(ROOT / "analysis/flowpanel/solve.jl"), str(run)], lambda: self.run_complete(run))
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
        self.tabs.setCurrentWidget(self.viewer)

    def view_results(self):
        try:
            folder = self.case / "results"
            data = tomllib.loads((folder / "coefficients.toml").read_text(encoding="utf-8"))
            self.show_file(folder / "manta.vtk", True)
            self.summary.setText(f"CL: {data['CL']:.5f}    CD (inviscid): {data['CD_inviscid']:.5f}    "
                f"Cm: {data['Cm']:.5f}\nCp: {data['Cp_min']:.3f} to {data['Cp_max']:.3f}. "
                "Preliminary: inspect pressure peaks and wake; check mesh convergence. Drag excludes friction.")
        except FileNotFoundError:
            self.error("No completed results for this case. Run a simulation or open an existing run's case.toml.")
        except Exception as error:
            self.error(error)

    def finalize(self):
        if self.viewer:
            self.viewer.finalize()
