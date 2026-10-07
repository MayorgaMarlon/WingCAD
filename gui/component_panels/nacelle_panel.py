"""Panel de propiedades de una góndola."""

from gui.display_text import display_label

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.materials import (
    buscar_material_por_densidad,
    listar_materiales,
)
from core.nacelle_parameters import NacelleParameters


class NacellePanel(QWidget):
    """Editor gráfico de los parámetros de una góndola."""

    recalcular_solicitado = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.componente = None
        self._crear_interfaz()

    @staticmethod
    def _crear_control_dimension(
        valor,
        minimo,
        maximo,
        decimales=2,
    ):
        control = QDoubleSpinBox()
        control.setRange(minimo, maximo)
        control.setValue(valor)
        control.setDecimals(decimales)
        control.setSingleStep(10.0)
        control.setSuffix(" mm")
        control.setKeyboardTracking(False)

        return control

    @staticmethod
    def _crear_control_porcentaje(
        valor,
        minimo,
        maximo,
    ):
        control = QDoubleSpinBox()
        control.setRange(minimo, maximo)
        control.setValue(valor)
        control.setDecimals(1)
        control.setSingleStep(1.0)
        control.setSuffix(" %")
        control.setKeyboardTracking(False)

        return control

    def _crear_interfaz(self):
        distribucion = QVBoxLayout(self)

        titulo = QLabel(
            "NACELLE PROPERTIES"
        )
        titulo.setStyleSheet(
            """
            font-size: 16px;
            font-weight: bold;
            padding: 8px;
            """
        )
        distribucion.addWidget(titulo)

        # =====================================================
        # Identification
        # =====================================================

        grupo_identificacion = QGroupBox(
            "Identification"
        )
        formulario_identificacion = QFormLayout(
            grupo_identificacion
        )

        self.nombre_control = QLineEdit(
            "Nacelle 1"
        )

        formulario_identificacion.addRow(
            "Name:",
            self.nombre_control,
        )

        distribucion.addWidget(
            grupo_identificacion
        )

        # =====================================================
        # External dimensions
        # =====================================================

        grupo_dimensiones = QGroupBox(
            "External dimensions"
        )
        formulario_dimensiones = QFormLayout(
            grupo_dimensiones
        )

        self.longitud_control = (
            self._crear_control_dimension(
                1800.0,
                100.0,
                50000.0,
            )
        )

        self.diametro_entrada_control = (
            self._crear_control_dimension(
                900.0,
                10.0,
                20000.0,
            )
        )

        self.diametro_maximo_control = (
            self._crear_control_dimension(
                1050.0,
                10.0,
                20000.0,
            )
        )

        self.diametro_salida_control = (
            self._crear_control_dimension(
                760.0,
                10.0,
                20000.0,
            )
        )

        self.espesor_pared_control = (
            self._crear_control_dimension(
                20.0,
                0.1,
                2000.0,
            )
        )
        self.espesor_pared_control.setSingleStep(
            1.0
        )

        formulario_dimensiones.addRow(
            "Length:",
            self.longitud_control,
        )
        formulario_dimensiones.addRow(
            "Inlet diameter:",
            self.diametro_entrada_control,
        )
        formulario_dimensiones.addRow(
            "Maximum diameter:",
            self.diametro_maximo_control,
        )
        formulario_dimensiones.addRow(
            "Outlet diameter:",
            self.diametro_salida_control,
        )
        formulario_dimensiones.addRow(
            "Wall thickness:",
            self.espesor_pared_control,
        )

        distribucion.addWidget(
            grupo_dimensiones
        )

        # =====================================================
        # Longitudinal distribution
        # =====================================================

        grupo_forma = QGroupBox(
            "Longitudinal distribution"
        )
        formulario_forma = QFormLayout(
            grupo_forma
        )

        self.posicion_diametro_maximo_control = (
            self._crear_control_porcentaje(
                35.0,
                15.0,
                75.0,
            )
        )

        self.secciones_control = QSpinBox()
        self.secciones_control.setRange(6, 80)
        self.secciones_control.setValue(18)
        self.secciones_control.setSingleStep(1)
        self.secciones_control.setKeyboardTracking(
            False
        )

        formulario_forma.addRow(
            "Maximum-diameter station:",
            self.posicion_diametro_maximo_control,
        )
        formulario_forma.addRow(
            "Loft sections:",
            self.secciones_control,
        )

        distribucion.addWidget(grupo_forma)

        # =====================================================
        # MATERIAL
        # =====================================================

        grupo_material = QGroupBox(
            "Material and mass model"
        )
        formulario_material = QFormLayout(
            grupo_material
        )

        self.material_control = QComboBox()

        for material in listar_materiales():
            self.material_control.addItem(
                display_label(material.nombre),
                material.densidad_kg_m3,
            )

        self.material_control.addItem(
            "Custom",
            "personalizado",
        )

        self.densidad_control = QDoubleSpinBox()
        self.densidad_control.setRange(
            0.1,
            30000.0,
        )
        self.densidad_control.setValue(
            1600.0
        )
        self.densidad_control.setDecimals(3)
        self.densidad_control.setSingleStep(
            100.0
        )
        self.densidad_control.setSuffix(
            " kg/m³"
        )
        self.densidad_control.setKeyboardTracking(
            False
        )

        self.modelo_masa_control = QComboBox()
        self.modelo_masa_control.addItem(
            "Actual wall volume",
            "solido",
        )
        self.modelo_masa_control.addItem(
            "Shell approximation",
            "carcasa",
        )

        self.espesor_masa_control = (
            self._crear_control_dimension(
                2.0,
                0.1,
                1000.0,
            )
        )
        self.espesor_masa_control.setSingleStep(
            0.5
        )

        ayuda_modelo = QLabel(
            "For a hollow nacelle, use the actual wall volume."
        )
        ayuda_modelo.setWordWrap(True)
        ayuda_modelo.setStyleSheet(
            """
            color: #666666;
            font-size: 11px;
            padding: 4px;
            """
        )

        formulario_material.addRow(
            "Material:",
            self.material_control,
        )
        formulario_material.addRow(
            "Density:",
            self.densidad_control,
        )
        formulario_material.addRow(
            "Mass model:",
            self.modelo_masa_control,
        )
        formulario_material.addRow(
            "Mass-model thickness:",
            self.espesor_masa_control,
        )
        formulario_material.addRow(
            ayuda_modelo
        )

        distribucion.addWidget(grupo_material)

        # =====================================================
        # BOTÓN DE RECÁLCULO
        # =====================================================

        self.boton_recalcular = QPushButton(
            "Generate nacelle"
        )
        self.boton_recalcular.setMinimumHeight(
            48
        )
        self.boton_recalcular.setStyleSheet(
            """
            QPushButton {
                font-weight: bold;
            }
            """
        )

        distribucion.addWidget(
            self.boton_recalcular
        )
        distribucion.addStretch()

        # =====================================================
        # CONEXIONES
        # =====================================================

        self.boton_recalcular.clicked.connect(
            self.recalcular_solicitado.emit
        )

        self.material_control.currentIndexChanged.connect(
            self._aplicar_material_seleccionado
        )

        self.modelo_masa_control.currentIndexChanged.connect(
            self._actualizar_estado_espesor
        )

        self._seleccionar_material_por_densidad(
            1600.0
        )
        self._actualizar_estado_espesor()

    def establecer_componente(
        self,
        componente,
    ):
        """Carga los valores de una góndola en el panel."""

        self.componente = componente

        self.nombre_control.setText(
            componente.nombre
        )

        parametros = componente.parametros

        self.longitud_control.setValue(
            parametros.length_mm
        )
        self.diametro_entrada_control.setValue(
            parametros.inlet_diameter_mm
        )
        self.diametro_maximo_control.setValue(
            parametros.max_diameter_mm
        )
        self.diametro_salida_control.setValue(
            parametros.outlet_diameter_mm
        )
        self.espesor_pared_control.setValue(
            parametros.wall_thickness_mm
        )

        self.posicion_diametro_maximo_control.setValue(
            parametros.max_diameter_position_ratio
            * 100.0
        )
        self.secciones_control.setValue(
            parametros.num_sections
        )

        self._seleccionar_material_por_densidad(
            componente.densidad_kg_m3
        )

        indice_modelo = (
            self.modelo_masa_control.findData(
                componente.modelo_masa
            )
        )

        if indice_modelo >= 0:
            self.modelo_masa_control.setCurrentIndex(
                indice_modelo
            )

        self.espesor_masa_control.setValue(
            componente.espesor_mm
        )

        self._actualizar_estado_espesor()

    def leer_nombre(self) -> str:
        """Devuelve el nombre escrito por el usuario."""

        nombre = self.nombre_control.text().strip()

        if not nombre:
            raise ValueError(
                "The nacelle name cannot be empty."
            )

        return nombre

    def leer_parametros(
        self,
    ) -> NacelleParameters:
        """Construye los parámetros usando los controles."""

        parametros = NacelleParameters(
            length_mm=(
                self.longitud_control.value()
            ),
            inlet_diameter_mm=(
                self.diametro_entrada_control.value()
            ),
            max_diameter_mm=(
                self.diametro_maximo_control.value()
            ),
            outlet_diameter_mm=(
                self.diametro_salida_control.value()
            ),
            wall_thickness_mm=(
                self.espesor_pared_control.value()
            ),
            max_diameter_position_ratio=(
                self.posicion_diametro_maximo_control.value()
                / 100.0
            ),
            num_sections=(
                self.secciones_control.value()
            ),
        )

        parametros.validar()

        return parametros

    def leer_densidad(self) -> float:
        """Devuelve la densidad seleccionada."""

        densidad = self.densidad_control.value()

        if densidad <= 0.0:
            raise ValueError(
                "Density must be greater than zero."
            )

        return densidad

    def leer_modelo_masa(self) -> str:
        """Devuelve el modelo usado para calcular la masa."""

        return self.modelo_masa_control.currentData()

    def leer_espesor(self) -> float:
        """Devuelve el espesor del modelo de masa."""

        espesor = self.espesor_masa_control.value()

        if espesor <= 0.0:
            raise ValueError(
                "Thickness must be greater than zero."
            )

        return espesor

    def _aplicar_material_seleccionado(
        self,
        *_,
    ):
        """Actualiza la densidad al elegir un material."""

        datos_material = (
            self.material_control.currentData()
        )

        if datos_material == "personalizado":
            self.densidad_control.setEnabled(True)
            return

        if datos_material is None:
            return

        self.densidad_control.setValue(
            float(datos_material)
        )
        self.densidad_control.setEnabled(False)

    def _seleccionar_material_por_densidad(
        self,
        densidad,
    ):
        """Selecciona el material correspondiente."""

        material = buscar_material_por_densidad(
            densidad
        )

        if material is None:
            indice = self.material_control.findData(
                "personalizado"
            )

            if indice >= 0:
                self.material_control.setCurrentIndex(
                    indice
                )

            self.densidad_control.setEnabled(True)
            self.densidad_control.setValue(
                densidad
            )
            return

        indice = self.material_control.findText(
            material.nombre
        )

        if indice >= 0:
            self.material_control.setCurrentIndex(
                indice
            )

        self.densidad_control.setValue(
            material.densidad_kg_m3
        )
        self.densidad_control.setEnabled(False)

    def _actualizar_estado_espesor(
        self,
        *_,
    ):
        """Habilita el espesor para el modelo de carcasa."""

        es_carcasa = (
            self.leer_modelo_masa()
            == "carcasa"
        )

        self.espesor_masa_control.setEnabled(
            es_carcasa
        )
