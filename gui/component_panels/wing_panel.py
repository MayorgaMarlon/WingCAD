"""Panel de propiedades para componentes de tipo ala."""

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

from components.wing import WingComponent
from core.parameters import WingParameters
from core.materials import (
    buscar_material_por_densidad,
    listar_materiales,
    obtener_material,
)

class WingPanel(QWidget):
    """Editor gráfico de parámetros de una superficie aerodinámica."""

    recalcular_solicitado = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.componente = None

        self._crear_interfaz()

    @staticmethod
    def _crear_decimal(
        valor,
        minimo,
        maximo,
        sufijo="",
        decimales=2,
    ):
        control = QDoubleSpinBox()
        control.setRange(minimo, maximo)
        control.setValue(valor)
        control.setDecimals(decimales)
        control.setSuffix(sufijo)
        control.setSingleStep(1.0)

        return control

    def _crear_interfaz(self):
        distribucion = QVBoxLayout(self)

        titulo = QLabel("WING PROPERTIES")
        titulo.setStyleSheet(
            """
            font-size: 16px;
            font-weight: bold;
            padding: 6px;
            """
        )

        distribucion.addWidget(titulo)

        grupo_identificacion = QGroupBox("Identification")
        formulario_identificacion = QFormLayout(
            grupo_identificacion
        )

        self.entrada_nombre = QLineEdit("Ala principal")

        formulario_identificacion.addRow(
            "Name:",
            self.entrada_nombre,
        )

        grupo_tipo = QGroupBox(
            "Surface configuration"
        )
        formulario_tipo = QFormLayout(grupo_tipo)

        self.entrada_modo_superficie = QComboBox()

        self.entrada_modo_superficie.addItem(
            "Full wing (symmetric)",
            "simetrica",
        )

        self.entrada_modo_superficie.addItem(
            "Negative half-wing",
            "semiala_positiva",
        )

        self.entrada_modo_superficie.addItem(
            "Semiala negativa",
            "semiala_negativa",
        )

        self.entrada_modo_superficie.setToolTip(
            "Use una Negative half-wing para una deriva vertical. "
            "El Placement define después su orientación."
        )

        formulario_tipo.addRow(
            "Surface type:",
            self.entrada_modo_superficie,
        )

        grupo_perfiles = QGroupBox(
            "Airfoils"
        )
        formulario_perfiles = QFormLayout(grupo_perfiles)

        self.entrada_perfil_raiz = QLineEdit("2412")
        self.entrada_perfil_punta = QLineEdit("2412")

        self.entrada_perfil_raiz.setMaxLength(4)
        self.entrada_perfil_punta.setMaxLength(4)

        formulario_perfiles.addRow(
            "Root airfoil:",
            self.entrada_perfil_raiz,
        )

        formulario_perfiles.addRow(
            "Tip airfoil:",
            self.entrada_perfil_punta,
        )

        grupo_Geometry = QGroupBox("Geometry")
        formulario_Geometry = QFormLayout(
            grupo_Geometry
        )

        self.entrada_cuerda_raiz = self._crear_decimal(
            1000.0,
            1.0,
            100000.0,
            " mm",
        )

        self.entrada_cuerda_punta = self._crear_decimal(
            500.0,
            1.0,
            100000.0,
            " mm",
        )

        self.entrada_semi_span = self._crear_decimal(
            4000.0,
            1.0,
            500000.0,
            " mm",
        )

        formulario_Geometry.addRow(
            "Root chord:",
            self.entrada_cuerda_raiz,
        )

        formulario_Geometry.addRow(
            "Tip chord:",
            self.entrada_cuerda_punta,
        )

        formulario_Geometry.addRow(
            "Semi-span:",
            self.entrada_semi_span,
        )

        grupo_angulos = QGroupBox("Sweep angle:")
        formulario_angulos = QFormLayout(grupo_angulos)

        self.entrada_flecha = self._crear_decimal(
            15.0,
            -45.0,
            75.0,
            "°",
        )

        self.entrada_diedro = self._crear_decimal(
            3.0,
            -20.0,
            45.0,
            "°",
        )

        self.entrada_torsion = self._crear_decimal(
            -3.0,
            -20.0,
            20.0,
            "°",
        )

        formulario_angulos.addRow(
            "Flecha:",
            self.entrada_flecha,
        )

        formulario_angulos.addRow(
            "Dihedral angle:",
            self.entrada_diedro,
        )

        formulario_angulos.addRow(
            "Tip twist:",
            self.entrada_torsion,
        )

        grupo_calidad = QGroupBox("Discretization and material")
        formulario_calidad = QFormLayout(grupo_calidad)

        self.entrada_puntos = QSpinBox()
        self.entrada_puntos.setRange(20, 300)
        self.entrada_puntos.setValue(60)

        self.entrada_secciones = QSpinBox()
        self.entrada_secciones.setRange(2, 50)
        self.entrada_secciones.setValue(10)
        self.entrada_material = QComboBox()
        self.entrada_material.addItem(
            "Personalizado",
            None,
        )

        for material in listar_materiales():
            self.entrada_material.addItem(
                material.nombre,
                material.identificador,
            )

        self.entrada_material.currentIndexChanged.connect(
            self._aplicar_material_seleccionado
        )
        self.entrada_densidad = self._crear_decimal(
            2700.0,
            0.1,
            30000.0,
            " kg/m³",
            1,
        )

        self.entrada_densidad.setSingleStep(100.0)
        self.entrada_modelo_masa = QComboBox()
        self.entrada_modelo_masa.addItem(
            "Solid",
            "solido",
        )
        self.entrada_modelo_masa.addItem(
            "Shell de pared delgada",
            "Shell",
        )

        self.entrada_espesor = self._crear_decimal(
            2.0,
            0.01,
            1000.0,
            " mm",
            2,
        )
        self.entrada_espesor.setSingleStep(0.5)

        self.entrada_modelo_masa.currentIndexChanged.connect(
            self._actualizar_estado_espesor
        )

        formulario_calidad.addRow(
            "Airfoil points:",
            self.entrada_puntos,
        )

        formulario_calidad.addRow(
            "Loft sections:",
            self.entrada_secciones,
        )
        formulario_calidad.addRow(
            "Mass model:",
            self.entrada_modelo_masa,
        )

        formulario_calidad.addRow(
            "Thickness:",
            self.entrada_espesor,
        )
        formulario_calidad.addRow(
            "Material:",
            self.entrada_material,
        )
        formulario_calidad.addRow(
            "Density:",
            self.entrada_densidad,
        )
        self._actualizar_estado_espesor()
        self.boton_recalcular = QPushButton(
            "Apply and rebuild"
        )

        self.boton_recalcular.setMinimumHeight(42)

        self.boton_recalcular.setStyleSheet(
            """
            QPushButton {
                background-color: #2878c8;
                color: white;
                font-weight: bold;
                border-radius: 5px;
            }

            QPushButton:hover {
                background-color: #3490e6;
            }
            """
        )

        self.boton_recalcular.clicked.connect(
            self.recalcular_solicitado.emit
        )

        distribucion.addWidget(grupo_identificacion)
        distribucion.addWidget(grupo_tipo)
        distribucion.addWidget(grupo_perfiles)
        distribucion.addWidget(grupo_Geometry)
        distribucion.addWidget(grupo_angulos)
        distribucion.addWidget(grupo_calidad)
        distribucion.addWidget(self.boton_recalcular)
        distribucion.addStretch()

    def leer_modo_superficie(self) -> str:
        return self.entrada_modo_superficie.currentData()

    def leer_parametros(self):
        """Construye los parámetros y actualiza el modo del componente."""

        parametros = WingParameters(
            perfil_raiz=(
                self.entrada_perfil_raiz.text().strip()
            ),
            perfil_punta=(
                self.entrada_perfil_punta.text().strip()
            ),
            cuerda_raiz_mm=(
                self.entrada_cuerda_raiz.value()
            ),
            cuerda_punta_mm=(
                self.entrada_cuerda_punta.value()
            ),
            semi_span_mm=(
                self.entrada_semi_span.value()
            ),
            flecha_grados=(
                self.entrada_flecha.value()
            ),
            diedro_grados=(
                self.entrada_diedro.value()
            ),
            torsion_punta_grados=(
                self.entrada_torsion.value()
            ),
            numero_puntos=(
                self.entrada_puntos.value()
            ),
            numero_secciones=(
                self.entrada_secciones.value()
            ),
        )

        parametros.validar()

        if self.componente is not None:
            self.componente.establecer_modo_superficie(
                self.leer_modo_superficie()
            )

        return parametros

    def leer_nombre(self):
        nombre = self.entrada_nombre.text().strip()

        if not Name:
            raise ValueError(
                "El nombre de la superficie no puede estar vacío."
            )

        return nombre

    def leer_densidad(self):
        return self.entrada_densidad.value()
    def leer_modelo_masa(self):
        return self.entrada_modelo_masa.currentData()

    def leer_espesor(self):
        return self.entrada_espesor.value()
    def _aplicar_material_seleccionado(
        self,
        *_,
    ) -> None:
        identificador = (
            self.entrada_material.currentData()
        )

        if identificador is None:
            self.entrada_densidad.setEnabled(True)
            return

        material = obtener_material(
            identificador
        )

        self.entrada_densidad.setValue(
            material.densidad_kg_m3
        )
        self.entrada_densidad.setEnabled(False)

    def _seleccionar_material_por_densidad(
        self,
        densidad_kg_m3: float,
    ) -> None:
        material = buscar_material_por_densidad(
            densidad_kg_m3
        )

        self.entrada_material.blockSignals(True)

        if material is None:
            self.entrada_material.setCurrentIndex(0)
            self.entrada_densidad.setEnabled(True)
        else:
            indice = self.entrada_material.findData(
                material.identificador
            )

            if indice >= 0:
                self.entrada_material.setCurrentIndex(
                    indice
                )
                self.entrada_densidad.setEnabled(False)
            else:
                self.entrada_material.setCurrentIndex(0)
                self.entrada_densidad.setEnabled(True)

        self.entrada_material.blockSignals(False)
    def _actualizar_estado_espesor(self, *_):
        es_Shell = (
            self.leer_modelo_masa()
            == "Shell"
        )
        self.entrada_espesor.setEnabled(
            es_Shell
        )
    def establecer_componente(self, componente):
        if not isinstance(componente, WingComponent):
            raise TypeError(
                "El panel solo admite componentes de tipo ala."
            )

        self.componente = componente

        parametros = componente.parametros

        self.entrada_nombre.setText(componente.nombre)

        indice_modo = self.entrada_modo_superficie.findData(
            componente.modo_superficie
        )

        self.entrada_modo_superficie.setCurrentIndex(
            max(indice_modo, 0)
        )

        self.entrada_perfil_raiz.setText(
            parametros.perfil_raiz
        )

        self.entrada_perfil_punta.setText(
            parametros.perfil_punta
        )

        self.entrada_cuerda_raiz.setValue(
            parametros.cuerda_raiz_mm
        )

        self.entrada_cuerda_punta.setValue(
            parametros.cuerda_punta_mm
        )

        self.entrada_semi_span.setValue(
            parametros.semi_span_mm
        )

        self.entrada_flecha.setValue(
            parametros.flecha_grados
        )

        self.entrada_diedro.setValue(
            parametros.diedro_grados
        )

        self.entrada_torsion.setValue(
            parametros.torsion_punta_grados
        )

        self.entrada_puntos.setValue(
            parametros.numero_puntos
        )

        self.entrada_secciones.setValue(
            parametros.numero_secciones
        )

        self.entrada_densidad.setValue(
            componente.densidad_kg_m3
        )
        self._seleccionar_material_por_densidad(
            componente.densidad_kg_m3
        )
        indice_modelo = (
            self.entrada_modelo_masa.findData(
                componente.modelo_masa
            )
        )

        self.entrada_modelo_masa.setCurrentIndex(
            max(indice_modelo, 0)
        )

        self.entrada_espesor.setValue(
            componente.espesor_mm
        )

        self._actualizar_estado_espesor()
    def limpiar_componente(self):
        self.componente = None

        self.entrada_nombre.setText("Nueva ala")

        self.entrada_modo_superficie.setCurrentIndex(0)
