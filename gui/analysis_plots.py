"""Saved-run plots displayed inside WingCAD; no VTK dependency."""
import json
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QPixmap, QDesktopServices
from PySide6.QtWidgets import QWidget,QVBoxLayout,QLabel,QTabWidget,QScrollArea,QPushButton,QSizePolicy


class PlotImage(QScrollArea):
    def __init__(self,path):
        super().__init__()
        self.original=QPixmap(str(path))
        if self.original.isNull():raise ValueError(f'Unable to load plot: {path.name}')
        self.label=QLabel()
        self.label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self.label.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Fixed)
        self.setWidget(self.label)
        self.setWidgetResizable(True)
        self.setStyleSheet('QScrollArea { background: white; border: none; } QLabel { background: white; }')

    def resizeEvent(self,event):
        super().resizeEvent(event)
        width=max(200,min(1500,self.viewport().width()-20))
        pixmap=self.original.scaledToWidth(width,Qt.TransformationMode.SmoothTransformation)
        self.label.setPixmap(pixmap)
        self.label.setFixedHeight(pixmap.height())


class AnalysisPlots(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent)
        layout=QVBoxLayout(self)
        self.title=QLabel();layout.addWidget(self.title)
        self.pages=QTabWidget();layout.addWidget(self.pages,1)
        note=QLabel('Saved WingCAD run only. No reference or experimental overlays. '
                    'Raw panel values; no smoothing. Preliminary: convergence is not established.')
        note.setWordWrap(True);layout.addWidget(note)
        export=QPushButton('Open PNG and CSV files')
        export.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.folder))))
        layout.addWidget(export)

    def load(self,folder):
        data=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
        self.folder=folder
        self.title.setText(data['title']);self.title.setToolTip(data['run']+'\n'+data['method'])
        while self.pages.count():
            widget=self.pages.widget(0);self.pages.removeTab(0);widget.deleteLater()
        for title,name in [('Pressure Cp','pressure.png'),('Pressure difference','delta_pressure.png'),('Spanwise loading','span_loading.png')]:
            self.pages.addTab(PlotImage(folder/name),title)
