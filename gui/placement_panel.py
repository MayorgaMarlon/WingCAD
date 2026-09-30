from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from geometry.placement import Placement


class PlacementPanel(QGroupBox):
    """
    Panel genérico para posicionar cualquier objeto CAD.

    No contiene lógica específica de alas, fuselajes o estabilizadores.
    """

    aplicar_solicitado = Signal(object)

    def __init__(self, parent=None):
        super().__init__("Position and orientation", parent)

        self._creando_interfaz = True

        self.x_control = self._crear_control_posicion()
        self.y_control = self._crear_control_posicion()
        self.z_control = self._crear_control_posicion()

        self.roll_control = self._crear_control_angulo()
        self.pitch_control = self._crear_control_angulo()
        self.yaw_control = self._crear_control_angulo()

        self.boton_aplicar = QPushButton("Apply position")
        self.boton_restablecer = QPushButton("Reset")

        self._construir_interfaz()
        self._conectar_eventos()

        self._creando_interfaz = False

    @staticmethod
    def _crear_control_posicion():
        control = QDoubleSpinBox()
        control.setRange(-1_000_000.0, 1_000_000.0)
        control.setDecimals(3)
        control.setSingleStep(10.0)
        control.setSuffix(" mm")
        control.setKeyboardTracking(False)
        return control

    @staticmethod
    def _crear_control_angulo():
        control = QDoubleSpinBox()
        control.setRange(-360.0, 360.0)
        control.setDecimals(3)
        control.setSingleStep(1.0)
        control.setSuffix("°")
        control.setKeyboardTracking(False)
        return control

    def _construir_interfaz(self):
        cuadricula = QGridLayout()

        cuadricula.addWidget(QLabel("X:"), 0, 0)
        cuadricula.addWidget(self.x_control, 0, 1)

        cuadricula.addWidget(QLabel("Y:"), 1, 0)
        cuadricula.addWidget(self.y_control, 1, 1)

        cuadricula.addWidget(QLabel("Z:"), 2, 0)
        cuadricula.addWidget(self.z_control, 2, 1)

        cuadricula.addWidget(QLabel("Roll:"), 3, 0)
        cuadricula.addWidget(self.roll_control, 3, 1)

        cuadricula.addWidget(QLabel("Pitch:"), 4, 0)
        cuadricula.addWidget(self.pitch_control, 4, 1)

        cuadricula.addWidget(QLabel("Yaw:"), 5, 0)
        cuadricula.addWidget(self.yaw_control, 5, 1)

        layout_botones = QGridLayout()
        layout_botones.addWidget(self.boton_aplicar, 0, 0)
        layout_botones.addWidget(self.boton_restablecer, 0, 1)

        layout_principal = QVBoxLayout(self)
        layout_principal.addLayout(cuadricula)
        layout_principal.addLayout(layout_botones)

    def _conectar_eventos(self):
        self.boton_aplicar.clicked.connect(self._solicitar_aplicacion)
        self.boton_restablecer.clicked.connect(self._restablecer)

    def obtener_placement(self) -> Placement:
        return Placement(
            x_mm=self.x_control.value(),
            y_mm=self.y_control.value(),
            z_mm=self.z_control.value(),
            roll_deg=self.roll_control.value(),
            pitch_deg=self.pitch_control.value(),
            yaw_deg=self.yaw_control.value(),
        )

    def establecer_placement(self, placement: Placement):
        """
        Carga los valores del objeto seleccionado sin emitir señales.
        """

        controles = (
            self.x_control,
            self.y_control,
            self.z_control,
            self.roll_control,
            self.pitch_control,
            self.yaw_control,
        )

        for control in controles:
            control.blockSignals(True)

        try:
            self.x_control.setValue(placement.x_mm)
            self.y_control.setValue(placement.y_mm)
            self.z_control.setValue(placement.z_mm)

            self.roll_control.setValue(placement.roll_deg)
            self.pitch_control.setValue(placement.pitch_deg)
            self.yaw_control.setValue(placement.yaw_deg)
        finally:
            for control in controles:
                control.blockSignals(False)

    def limpiar(self):
        self.establecer_placement(Placement())
        self.setEnabled(False)

    def habilitar(self, habilitado: bool = True):
        self.setEnabled(habilitado)

    def _solicitar_aplicacion(self):
        if self._creando_interfaz:
            return

        placement = self.obtener_placement()
        placement.validar()

        self.aplicar_solicitado.emit(placement)

    def _restablecer(self):
        placement = Placement()

        self.establecer_placement(placement)
        self.aplicar_solicitado.emit(placement)