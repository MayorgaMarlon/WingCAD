"""Panel gráfico para editar un fuselaje paramétrico."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
    QComboBox,
)
from core.materials import (
    buscar_material_por_densidad,
    listar_materiales,
    obtener_material,
)
from core.fuselage_parameters import FuselageParameters


class FuselagePanel(QWidget):
    """Editor de las propiedades de un fuselaje."""

    recalcular_solicitado = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.componente = None
        self._crear_interfaz()

    @staticmethod
    def _crear_control_dimension(
        valor: float,
        minimo: float = 1.0,
        maximo: float = 1_000_000.0,
    ):
        control = QDoubleSpinBox()

        control.setRange(
            minimo,
            maximo,
        )
        control.setDecimals(2)
        control.setSingleStep(100.0)
        control.setSuffix(" mm")
        control.setValue(valor)
        control.setKeyboardTracking(False)

        return control

    @staticmethod
    def _crear_control_porcentaje(
        valor: float,
        minimo: float,
        maximo: float,
    ):
        control = QDoubleSpinBox()

        control.setRange(
            minimo,
            maximo,
        )
        control.setDecimals(1)
        control.setSingleStep(1.0)
        control.setSuffix(" %")
        control.setValue(valor)
        control.setKeyboardTracking(False)

        return control

    def _crear_interfaz(self):
        layout_principal = QVBoxLayout(self)

        titulo = QLabel(
            "FUSELAGE PROPERTIES"
        )
        titulo.setStyleSheet(
            """
            font-size: 15px;
            font-weight: bold;
            padding: 8px;
            """
        )

        layout_principal.addWidget(
            titulo
        )

        # -----------------------------------------------------
        # Identification
        # -----------------------------------------------------

        grupo_identificacion = QGroupBox(
            "Identification"
        )
        formulario_identificacion = QFormLayout(
            grupo_identificacion
        )

        self.nombre_control = QLineEdit(
            "Fuselaje principal"
        )

        formulario_identificacion.addRow(
            "Name:",
            self.nombre_control,
        )

        layout_principal.addWidget(
            grupo_identificacion
        )

        # -----------------------------------------------------
        # Dimensiones
        # -----------------------------------------------------

        grupo_dimensiones = QGroupBox(
            "External dimensions"
        )
        formulario_dimensiones = QFormLayout(
            grupo_dimensiones
        )

        self.longitud_control = (
            self._crear_control_dimension(
                8000.0
            )
        )

        self.ancho_control = (
            self._crear_control_dimension(
                1200.0
            )
        )

        self.altura_control = (
            self._crear_control_dimension(
                1400.0
            )
        )

        formulario_dimensiones.addRow(
            "Length:",
            self.longitud_control,
        )
        formulario_dimensiones.addRow(
            "Maximum width:",
            self.ancho_control,
        )
        formulario_dimensiones.addRow(
            "Maximum height:",
            self.altura_control,
        )

        layout_principal.addWidget(
            grupo_dimensiones
        )

        # -----------------------------------------------------
        # Forma longitudinal
        # -----------------------------------------------------

        grupo_forma = QGroupBox(
            "Longitudinal distribution"
        )
        formulario_forma = QFormLayout(
            grupo_forma
        )

        self.nariz_control = (
            self._crear_control_porcentaje(
                valor=20.0,
                minimo=5.0,
                maximo=45.0,
            )
        )

        self.cola_control = (
            self._crear_control_porcentaje(
                valor=30.0,
                minimo=5.0,
                maximo=60.0,
            )
        )

        self.redondez_nariz_control = QDoubleSpinBox()
        self.redondez_nariz_control.setRange(
            0.40,
            2.50,
        )
        self.redondez_nariz_control.setDecimals(
            2
        )
        self.redondez_nariz_control.setSingleStep(
            0.05
        )
        self.redondez_nariz_control.setValue(
            1.00
        )
        self.redondez_nariz_control.setKeyboardTracking(
            False
        )

        self.afinamiento_cola_control = QDoubleSpinBox()
        self.afinamiento_cola_control.setRange(
            0.40,
            2.50,
        )
        self.afinamiento_cola_control.setDecimals(
            2
        )
        self.afinamiento_cola_control.setSingleStep(
            0.05
        )
        self.afinamiento_cola_control.setValue(
            1.45
        )
        self.afinamiento_cola_control.setKeyboardTracking(
            False
        )
        self.seccion_final_cola_control = (
            self._crear_control_porcentaje(
                valor=0.0,
                minimo=0.0,
                maximo=35.0,
            )
        )
        self.secciones_control = QSpinBox()
        self.secciones_control.setRange(
            6,
            100,
        )
        self.secciones_control.setValue(
            32
        )

        formulario_forma.addRow(
            "Nose length:",
            self.nariz_control,
        )
        formulario_forma.addRow(
            "Tail length:",
            self.cola_control,
        )
        formulario_forma.addRow(
            "Nose roundness:",
            self.redondez_nariz_control,
        )
        formulario_forma.addRow(
            "Tail taper:",
            self.afinamiento_cola_control,
        )
        formulario_forma.addRow(
            "Tail-end section:",
            self.seccion_final_cola_control,
        )
        formulario_forma.addRow(
            "Loft sections:",
            self.secciones_control,
        )

        layout_principal.addWidget(
            grupo_forma
        )

        # -----------------------------------------------------
        # Material
        # -----------------------------------------------------

        grupo_material = QGroupBox(
            "Material and mass model"
        )
        formulario_material = QFormLayout(
            grupo_material
        )
        self.material_control = QComboBox()
        self.material_control.addItem(
            "Personalizado",
            None,
        )

        for material in listar_materiales():
            self.material_control.addItem(
                material.nombre,
                material.identificador,
            )

        self.material_control.currentIndexChanged.connect(
            self._aplicar_material_seleccionado
        )
        self.densidad_control = QDoubleSpinBox()
        self.densidad_control.setRange(
            0.001,
            100_000.0,
        )
        self.densidad_control.setDecimals(
            3
        )
        self.densidad_control.setSingleStep(
            100.0
        )
        self.densidad_control.setSuffix(
            " kg/m³"
        )
        self.densidad_control.setValue(
            2700.0
        )
        self.densidad_control.setKeyboardTracking(
            False
        )
        formulario_material.addRow(
            "Material:",
            self.material_control,
        )
        formulario_material.addRow(
            "Density:",
        self.densidad_control,
        )

        layout_principal.addWidget(
            grupo_material
        )
        self.modelo_masa_control = QComboBox()
        self.modelo_masa_control.addItem(
            "Solid",
            "solido",
        )
        self.modelo_masa_control.addItem(
            "Shell de pared delgada",
            "carcasa",
        )

        self.espesor_control = QDoubleSpinBox()
        self.espesor_control.setRange(
            0.01,
            1000.0,
        )
        self.espesor_control.setDecimals(2)
        self.espesor_control.setSingleStep(0.5)
        self.espesor_control.setSuffix(" mm")
        self.espesor_control.setValue(2.0)
        self.espesor_control.setKeyboardTracking(False)

        self.modelo_masa_control.currentIndexChanged.connect(
            self._actualizar_estado_espesor
        )

        formulario_material.addRow(
            "Mass model:",
            self.modelo_masa_control,
        )

        formulario_material.addRow(
            "Thickness:",
            self.espesor_control,
        )
        self._actualizar_estado_espesor()
        # -----------------------------------------------------
        # Botón de construcción
        # -----------------------------------------------------

        self.boton_recalcular = QPushButton(
            "Generate fuselage"
        )
        self.boton_recalcular.setMinimumHeight(
            42
        )
        self.boton_recalcular.setStyleSheet(
            """
            font-weight: bold;
            padding: 8px;
            """
        )

        self.boton_recalcular.clicked.connect(
            self.recalcular_solicitado.emit
        )

        layout_principal.addWidget(
            self.boton_recalcular
        )
        layout_principal.addStretch()

    def establecer_componente(
        self,
        componente,
    ):
        """Carga en el panel los valores del fuselaje."""

        self.componente = componente
        parametros = componente.parametros

        self.nombre_control.setText(
            componente.nombre
        )
        self.longitud_control.setValue(
            parametros.length_mm
        )
        self.ancho_control.setValue(
            parametros.max_width_mm
        )
        self.altura_control.setValue(
            parametros.max_height_mm
        )
        self.nariz_control.setValue(
            parametros.nose_ratio * 100.0
        )
        self.cola_control.setValue(
            parametros.tail_ratio * 100.0
        )

        self.redondez_nariz_control.setValue(
            getattr(
                parametros,
                "nose_roundness",
                1.00,
            )
        )

        self.afinamiento_cola_control.setValue(
            getattr(
                parametros,
                "tail_roundness",
                1.45,
            )
        )
        self.seccion_final_cola_control.setValue(
            getattr(
                parametros,
                "tail_end_ratio",
                0.0,
            )
            * 100.0
        )
        self.secciones_control.setValue(
            parametros.num_sections
        )
        self.densidad_control.setValue(
            componente.densidad_kg_m3
        )
        self._seleccionar_material_por_densidad(
            componente.densidad_kg_m3
        )
        indice_modelo = (
            self.modelo_masa_control.findData(
                componente.modelo_masa
            )
        )

        self.modelo_masa_control.setCurrentIndex(
            max(
                indice_modelo,
                0,
            )
        )

        self.espesor_control.setValue(
            componente.espesor_mm
        )

        self._actualizar_estado_espesor()
    def leer_nombre(self) -> str:
        nombre = (
            self.nombre_control
            .text()
            .strip()
        )

        if not Name:
            raise ValueError(
                "El nombre del fuselaje "
                "no puede estar vacío."
            )

        return nombre

    def leer_parametros(
        self,
    ) -> FuselageParameters:
        """Obtiene los parámetros introducidos en el panel."""

        parametros = FuselageParameters(
            length_mm=(
                self.longitud_control.value()
            ),
            max_width_mm=(
                self.ancho_control.value()
            ),
            max_height_mm=(
                self.altura_control.value()
            ),
            nose_ratio=(
                self.nariz_control.value()
                / 100.0
            ),
            tail_ratio=(
                self.cola_control.value()
                / 100.0
            ),
            nose_roundness=(
                self.redondez_nariz_control.value()
            ),
            tail_roundness=(
                self.afinamiento_cola_control.value()
            ),
            tail_end_ratio=(
                self.seccion_final_cola_control.value()
                / 100.0
            ),
            num_sections=(
                self.secciones_control.value()
            ),
        )

        parametros.validar()
        return parametros

    def leer_densidad(self) -> float:
        densidad = (
            self.densidad_control.value()
        )

        if densidad <= 0.0:
            raise ValueError(
                "La densidad debe ser "
                "mayor que cero."
            )

        return densidad

    def leer_modelo_masa(self) -> str:
        return (
            self.modelo_masa_control
            .currentData()
        )

    def leer_espesor(self) -> float:
        espesor = (
            self.espesor_control.value()
        )

        if espesor <= 0.0:
            raise ValueError(
                "El espesor debe ser "
                "mayor que cero."
            )

        return espesor
    def _aplicar_material_seleccionado(
        self,
        *_,
    ) -> None:
        identificador = (
            self.material_control.currentData()
        )

        if identificador is None:
            self.densidad_control.setEnabled(True)
            return

        material = obtener_material(
            identificador
        )

        self.densidad_control.setValue(
            material.densidad_kg_m3
        )
        self.densidad_control.setEnabled(False)

    def _seleccionar_material_por_densidad(
        self,
        densidad_kg_m3: float,
    ) -> None:
        material = buscar_material_por_densidad(
            densidad_kg_m3
        )

        self.material_control.blockSignals(True)

        if material is None:
            self.material_control.setCurrentIndex(0)
            self.densidad_control.setEnabled(True)
        else:
            indice = self.material_control.findData(
                material.identificador
            )

            if indice >= 0:
                self.material_control.setCurrentIndex(
                    indice
                )
                self.densidad_control.setEnabled(False)
            else:
                self.material_control.setCurrentIndex(0)
                self.densidad_control.setEnabled(True)

        self.material_control.blockSignals(False)
    def _actualizar_estado_espesor(
        self,
        *_,
    ):
        es_carcasa = (
            self.leer_modelo_masa()
            == "Shell"
        )

        self.espesor_control.setEnabled(
            es_carcasa
        )