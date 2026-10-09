"""Ventana principal del modelador aeronáutico."""

from gui.display_text import display_label, display_error

import os
from pathlib import Path

os.environ.setdefault("QT_API", "pyside6")

import vtk
from PySide6.QtCore import Qt, QTimer, QLocale
from PySide6.QtWidgets import (
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from vtkmodules.qt.QVTKRenderWindowInteractor import (
    QVTKRenderWindowInteractor,
)

from app.application import AeroApplication
from components.fuselage import FuselageComponent
from components.nacelle import NacelleComponent
from components.wing import WingComponent
from core.exporter import (
    EXPORT_FILTERS,
    exportar_proyecto,
    exportar_geometria,
)
from core.viewer import convertir_shape_a_vtk
from gui.component_panels.fuselage_panel import FuselagePanel
from gui.component_panels.nacelle_panel import NacellePanel
from gui.component_panels.wing_panel import WingPanel
from gui.document_tree import DocumentTree
from gui.placement_panel import PlacementPanel
from gui.flowpanel_panel import FlowPanelPanel
from geometry.placement import Placement


class MainWindow(QMainWindow):
    """Interfaz principal del modelador aeronáutico."""

    def __init__(self):
        QLocale.setDefault(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
        super().__init__()

        self.aplicacion = AeroApplication()
        self.objeto_actual = None

        self.actores_objetos = {}

        # CG rojo: componente seleccionado.
        self.actor_cg = None

        # CG verde: ensamblaje completo.
        self.actor_cg_global = None

        self.limites_modelo = None

        self.setWindowTitle(
            "Parametric Aircraft Modeler"
        )
        self.resize(1450, 900)

        self._crear_interfaz()
        self._configurar_visualizador()

        QTimer.singleShot(
            200,
            self._iniciar_aplicacion,
        )

    def _crear_interfaz(self):
        """Construye la interfaz general."""

        widget_central = QWidget()
        distribucion_principal = QHBoxLayout(
            widget_central
        )

        # =====================================================
        # PANEL IZQUIERDO
        # =====================================================

        contenido_panel = QWidget()
        distribucion_panel = QVBoxLayout(
            contenido_panel
        )

        titulo = QLabel(
            "AIRCRAFT MODEL"
        )
        titulo.setStyleSheet(
            """
            font-size: 17px;
            font-weight: bold;
            padding: 8px;
            """
        )
        distribucion_panel.addWidget(titulo)
        # -----------------------------------------------------
        # Archivo de proyecto
        # -----------------------------------------------------

        botones_proyecto = QGridLayout()

        self.boton_nuevo_proyecto = QPushButton(
            "New project"
        )
        self.boton_abrir_proyecto = QPushButton(
            "Open project"
        )
        self.boton_guardar_proyecto = QPushButton(
            "Save project"
        )
        self.boton_propiedades_globales = QPushButton(
            "Global properties"
        )

        self.boton_nuevo_proyecto.clicked.connect(
            self.nuevo_proyecto
        )
        self.boton_abrir_proyecto.clicked.connect(
            self.abrir_proyecto
        )
        self.boton_guardar_proyecto.clicked.connect(
            self.guardar_proyecto
        )
        self.boton_propiedades_globales.clicked.connect(
            self.mostrar_propiedades_globales
        )

        botones_proyecto.addWidget(
            self.boton_nuevo_proyecto,
            0,
            0,
        )
        botones_proyecto.addWidget(
            self.boton_abrir_proyecto,
            0,
            1,
        )
        botones_proyecto.addWidget(
            self.boton_guardar_proyecto,
            1,
            0,
            1,
            2,
        )
        botones_proyecto.addWidget(
            self.boton_propiedades_globales,
            2,
            0,
            1,
            2,
        )

        distribucion_panel.addLayout(
            botones_proyecto
        )
        # -----------------------------------------------------
        # Botones de componentes
        # -----------------------------------------------------

        botones_componentes = QGridLayout()

        self.boton_nueva_ala = QPushButton(
            "New wing"
        )
        self.boton_nuevo_fuselaje = QPushButton(
            "New fuselage"
        )
        self.boton_estabilizador_horizontal = QPushButton(
            "Horizontal stabilizer"
        )
        self.boton_estabilizador_vertical = QPushButton(
            "Vertical stabilizer"
        )
        self.boton_nueva_gondola = QPushButton(
            "New nacelle"
        )
        self.boton_eliminar = QPushButton(
            "Delete"
        )
        self.boton_ordenar_componentes = QPushButton(
            "Arrange components"
        )

        self.boton_nueva_ala.clicked.connect(
            self.crear_nueva_ala
        )
        self.boton_nuevo_fuselaje.clicked.connect(
            self.crear_nuevo_fuselaje
        )
        self.boton_estabilizador_horizontal.clicked.connect(
            self.crear_estabilizador_horizontal
        )
        self.boton_estabilizador_vertical.clicked.connect(
            self.crear_estabilizador_vertical
        )
        self.boton_nueva_gondola.clicked.connect(
            self.crear_nueva_gondola
        )
        self.boton_eliminar.clicked.connect(
            self.eliminar_objeto_actual
        )
        self.boton_ordenar_componentes.clicked.connect(
            self.ordenar_componentes
        )

        botones_componentes.addWidget(
            self.boton_nueva_ala,
            0,
            0,
        )
        botones_componentes.addWidget(
            self.boton_nuevo_fuselaje,
            0,
            1,
        )
        botones_componentes.addWidget(
            self.boton_estabilizador_horizontal,
            1,
            0,
        )
        botones_componentes.addWidget(
            self.boton_estabilizador_vertical,
            1,
            1,
        )
        botones_componentes.addWidget(
            self.boton_nueva_gondola,
            2,
            0,
            1,
            2,
        )
        botones_componentes.addWidget(
            self.boton_eliminar,
            3,
            0,
            1,
            2,
        )
        botones_componentes.addWidget(
            self.boton_ordenar_componentes,
            4,
            0,
            1,
            2,
        )

        distribucion_panel.addLayout(
            botones_componentes
        )
                # -----------------------------------------------------
        # Árbol del documento
        # -----------------------------------------------------

        grupo_documento = QGroupBox(
            "Project"
        )

        distribucion_documento = QVBoxLayout(
            grupo_documento
        )

        self.arbol_documento = DocumentTree()
        self.arbol_documento.setMinimumHeight(140)
        self.arbol_documento.setMaximumHeight(200)

        self.arbol_documento.establecer_documento(
            self.aplicacion.documento
        )

        self.arbol_documento.objeto_seleccionado.connect(
            self._seleccionar_objeto
        )

        self.arbol_documento.visibilidad_modificada.connect(
            self._cambiar_visibilidad
        )

        distribucion_documento.addWidget(
            self.arbol_documento
        )

        distribucion_panel.addWidget(
            grupo_documento
        )
        # -----------------------------------------------------
        # Editores de componentes
        # -----------------------------------------------------

        grupo_propiedades = QGroupBox(
            "Object properties"
        )
        distribucion_propiedades = QVBoxLayout(
            grupo_propiedades
        )

        self.editores_componentes = QStackedWidget()

        self.panel_sin_objeto = QLabel(
            "Select an object in the document."
        )
        self.panel_sin_objeto.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.panel_sin_objeto.setWordWrap(True)

        self.panel_ala = WingPanel()
        self.panel_ala.recalcular_solicitado.connect(
            self.recalcular_objeto_actual
        )

        self.panel_fuselaje = FuselagePanel()
        self.panel_fuselaje.recalcular_solicitado.connect(
            self.recalcular_objeto_actual
        )

        self.panel_gondola = NacellePanel()
        self.panel_gondola.recalcular_solicitado.connect(
            self.recalcular_objeto_actual
        )

        self.editores_componentes.addWidget(
            self.panel_sin_objeto
        )
        self.editores_componentes.addWidget(
            self.panel_ala
        )
        self.editores_componentes.addWidget(
            self.panel_fuselaje
        )
        self.editores_componentes.addWidget(
            self.panel_gondola
        )

        self.editores_componentes.setCurrentWidget(
            self.panel_sin_objeto
        )

        distribucion_propiedades.addWidget(
            self.editores_componentes
        )
        distribucion_panel.addWidget(
            grupo_propiedades
        )

        # -----------------------------------------------------
        # Posición general del objeto
        # -----------------------------------------------------

        self.panel_placement = PlacementPanel()
        self.panel_placement.setEnabled(False)
        self.panel_placement.aplicar_solicitado.connect(
            self.aplicar_placement_objeto_actual
        )

        distribucion_panel.addWidget(
            self.panel_placement
        )

        # -----------------------------------------------------
        # Exportación
        # -----------------------------------------------------

        self.boton_exportar = QPushButton(
            "Export selected object..."
        )
        self.boton_exportar.setMinimumHeight(38)
        self.boton_exportar.setToolTip(
            "Choose STEP or BREP for CAD, STL for printing, GLB or OBJ for visualization."
        )
        self.boton_exportar.setEnabled(False)
        self.boton_exportar.clicked.connect(
            self.exportar_objeto
        )

        self.boton_exportar_proyecto = QPushButton(
            "Export project..."
        )
        self.boton_exportar_proyecto.setMinimumHeight(
            42
        )
        self.boton_exportar_proyecto.setToolTip(
            "Export all valid components. STEP is exported as a multibody part. "
            "STL keeps overlapping bodies; it does not join them for printing."
        )
        self.boton_exportar_proyecto.clicked.connect(
            self.exportar_proyecto_completo
        )

        distribucion_panel.addWidget(
            self.boton_exportar
        )
        distribucion_panel.addWidget(
            self.boton_exportar_proyecto
        )

        # -----------------------------------------------------
        # Resultados
        # -----------------------------------------------------

        grupo_resultados = QGroupBox(
            "Results"
        )
        distribucion_resultados = QVBoxLayout(
            grupo_resultados
        )

        self.etiqueta_resultados = QLabel(
            "Document ready."
        )
        self.etiqueta_resultados.setWordWrap(True)
        self.etiqueta_resultados.setAlignment(
            Qt.AlignmentFlag.AlignTop
            | Qt.AlignmentFlag.AlignLeft
        )
        self.etiqueta_resultados.setMinimumHeight(
            220
        )
        self.etiqueta_resultados.setStyleSheet(
            """
            padding: 8px;
            background-color: #eeeeee;
            font-family: Consolas;
            """
        )

        distribucion_resultados.addWidget(
            self.etiqueta_resultados
        )
        distribucion_panel.addWidget(
            grupo_resultados
        )
        distribucion_panel.addStretch()

        desplazamiento_panel = QScrollArea()
        desplazamiento_panel.setWidgetResizable(True)
        desplazamiento_panel.setFixedWidth(410)
        desplazamiento_panel.setWidget(
            contenido_panel
        )

        # =====================================================
        # VISUALIZADOR 3D
        # =====================================================

        grupo_visualizador = QGroupBox(
            "3D View"
        )
        distribucion_visualizador = QVBoxLayout(
            grupo_visualizador
        )

        barra_vistas = QHBoxLayout()

        self.boton_isometrica = QPushButton(
            "Isometric"
        )
        self.boton_superior = QPushButton(
            "Top"
        )
        self.boton_frontal = QPushButton(
            "Front"
        )
        self.boton_lateral = QPushButton(
            "Side"
        )
        self.boton_ajustar = QPushButton(
            "Fit"
        )
        self.boton_aristas = QPushButton(
            "Edges"
        )
        self.boton_aristas.setCheckable(True)

        self.boton_isometrica.clicked.connect(
            self.vista_isometrica
        )
        self.boton_superior.clicked.connect(
            self.vista_superior
        )
        self.boton_frontal.clicked.connect(
            self.vista_frontal
        )
        self.boton_lateral.clicked.connect(
            self.vista_lateral
        )
        self.boton_ajustar.clicked.connect(
            self.ajustar_vista
        )
        self.boton_aristas.toggled.connect(
            self.alternar_aristas
        )

        barra_vistas.addWidget(
            self.boton_isometrica
        )
        barra_vistas.addWidget(
            self.boton_superior
        )
        barra_vistas.addWidget(
            self.boton_frontal
        )
        barra_vistas.addWidget(
            self.boton_lateral
        )
        barra_vistas.addWidget(
            self.boton_ajustar
        )
        barra_vistas.addWidget(
            self.boton_aristas
        )

        self.visualizador = QVTKRenderWindowInteractor(
            grupo_visualizador
        )

        distribucion_visualizador.addLayout(
            barra_vistas
        )
        distribucion_visualizador.addWidget(
            self.visualizador
        )

        distribucion_principal.addWidget(
            desplazamiento_panel
        )
        workspace_tabs = QTabWidget()
        workspace_tabs.addTab(grupo_visualizador, "Design")
        self.analysis_panel = FlowPanelPanel(self.aplicacion, self)
        workspace_tabs.addTab(self.analysis_panel, "Analysis / FLOWPanel")
        # Modelling tools belong to Design; analysis uses the full window width.
        workspace_tabs.currentChanged.connect(lambda index: desplazamiento_panel.setVisible(index == 0))
        distribucion_principal.addWidget(workspace_tabs, 1)

        self.setCentralWidget(
            widget_central
        )

    def _configurar_visualizador(self):
        """Configura la escena VTK."""

        self.renderer = vtk.vtkRenderer()

        self.renderer.SetBackground(
            0.08,
            0.10,
            0.14,
        )
        self.renderer.SetBackground2(
            0.28,
            0.33,
            0.40,
        )
        self.renderer.GradientBackgroundOn()
        self.renderer.AutomaticLightCreationOn()

        ventana = (
            self.visualizador.GetRenderWindow()
        )
        ventana.AddRenderer(
            self.renderer
        )

        self.interactor = ventana.GetInteractor()
        self.interactor.SetInteractorStyle(
            vtk.vtkInteractorStyleTrackballCamera()
        )

    def _iniciar_aplicacion(self):
        """Inicializa VTK y crea el primer componente."""

        self.interactor.Initialize()

        if not self.aplicacion.documento.objetos:
            self.crear_nueva_ala()

    def nuevo_proyecto(self):
        """Crea un proyecto nuevo con su ala inicial."""

        respuesta = QMessageBox.question(
            self,
            "New project",
            "The current model will be discarded. Do you want to continue?",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if respuesta != QMessageBox.StandardButton.Yes:
            return

        self.aplicacion.nuevo_documento()
        self._restablecer_interfaz_documento()
        self.crear_nueva_ala()

    def guardar_proyecto(self):
        """Guarda todos los parámetros en un archivo .wingcad."""

        carpeta = (
            Path(__file__).resolve().parents[1]
            / "projects"
        )
        carpeta.mkdir(
            parents=True,
            exist_ok=True,
        )

        nombre = (
            self.aplicacion.documento.nombre.strip()
            or "project"
        )

        sugerido = carpeta / (
            f"{nombre.replace(' ', '_')}.wingcad"
        )

        archivo, _ = QFileDialog.getSaveFileName(
            self,
            "Save WingCAD project",
            str(sugerido),
            "WingCAD project (*.wingcad)",
            options=QFileDialog.Option.DontUseNativeDialog,
        )

        if not archivo:
            return

        try:
            ruta = self.aplicacion.guardar_proyecto(
                archivo
            )

            QMessageBox.information(
                self,
                "Project saved",
                f"Project saved to:\n{ruta}",
            )

        except Exception as error:
            QMessageBox.critical(
                self,
                "Unable to save project",
                display_error(error),
            )

    def abrir_proyecto(self):
        """Abre un proyecto y reconstruye la escena."""

        carpeta = (
            Path(__file__).resolve().parents[1]
            / "projects"
        )
        carpeta.mkdir(
            parents=True,
            exist_ok=True,
        )

        archivo, _ = QFileDialog.getOpenFileName(
            self,
            "Open WingCAD project",
            str(carpeta),
            "WingCAD project (*.wingcad)",
            options=QFileDialog.Option.DontUseNativeDialog,
        )

        if not archivo:
            return

        try:
            self.aplicacion.abrir_proyecto(
                archivo
            )

            self._restablecer_interfaz_documento()
            self._actualizar_escena_documento()
            self.ajustar_vista()

            QMessageBox.information(
                self,
                "Project opened",
                f"Project loaded:\n{archivo}",
            )

        except Exception as error:
            QMessageBox.critical(
                self,
                "Unable to open project",
                display_error(error),
            )

    def _restablecer_interfaz_documento(self):
        """Actualiza la interfaz para el documento actual."""

        self.objeto_actual = None
        self.analysis_panel.document_changed()

        self.arbol_documento.establecer_documento(
            self.aplicacion.documento
        )

        self.editores_componentes.setCurrentWidget(
            self.panel_sin_objeto
        )

        self.panel_placement.limpiar()
        self.panel_placement.habilitar(False)

        self.boton_exportar.setEnabled(False)

        self.etiqueta_resultados.setText(
            "Select an object in the project."
        )
    def _ordenar_componentes_automaticamente(self):
        """
        Coloca automáticamente alas, estabilizadores y góndolas
        utilizando el fuselaje principal como referencia.
        """

        longitud_mm = 8000.0
        ancho_mm = 1200.0
        altura_mm = 1400.0
        semienvergadura_mm = 4000.0

        origen_x_mm = 0.0
        origen_y_mm = 0.0
        origen_z_mm = 0.0

        fuselaje_referencia = None
        ala_principal = None

        # -----------------------------------------------------
        # Buscar el fuselaje principal
        # -----------------------------------------------------

        for objeto in self.aplicacion.documento.objetos:
            if isinstance(
                objeto,
                FuselageComponent,
            ):
                fuselaje_referencia = objeto

                if objeto.nombre.lower().startswith(
                    ("fuselaje principal", "main fuselage")
                ):
                    break

        if fuselaje_referencia is not None:
            parametros_fuselaje = (
                fuselaje_referencia.parametros
            )

            longitud_mm = float(
                parametros_fuselaje.length_mm
            )
            ancho_mm = float(
                parametros_fuselaje.max_width_mm
            )
            altura_mm = float(
                parametros_fuselaje.max_height_mm
            )

            origen_x_mm = float(
                fuselaje_referencia.placement.x_mm
            )
            origen_y_mm = float(
                fuselaje_referencia.placement.y_mm
            )
            origen_z_mm = float(
                fuselaje_referencia.placement.z_mm
            )

        # -----------------------------------------------------
        # Buscar el ala principal
        # -----------------------------------------------------

        for objeto in self.aplicacion.documento.objetos:
            if not isinstance(
                objeto,
                WingComponent,
            ):
                continue

            if objeto.nombre.strip().lower() in (
                "ala principal", "main wing"
            ):
                ala_principal = objeto
                break

        if ala_principal is not None:
            semienvergadura_mm = float(
                ala_principal.parametros.semi_span_mm
            )

        # -----------------------------------------------------
        # Posiciones principales
        # -----------------------------------------------------

        posicion_ala_x = (
            origen_x_mm
            + 0.38 * longitud_mm
        )

        posicion_cola_x = (
            origen_x_mm
            + 0.78 * longitud_mm
        )

        posicion_vertical_x = (
            origen_x_mm
            + 0.76 * longitud_mm
        )

        posicion_horizontal_z = (
            origen_z_mm
            + 0.12 * altura_mm
        )

        posicion_vertical_z = (
            origen_z_mm
            + 0.36 * altura_mm
        )

        # -----------------------------------------------------
        # Ordenar alas y estabilizadores
        # -----------------------------------------------------

        for objeto in self.aplicacion.documento.objetos:
            if not isinstance(
                objeto,
                WingComponent,
            ):
                continue

            nombre = objeto.nombre.strip().lower()

            if nombre in ("ala principal", "main wing"):
                objeto.establecer_placement(
                    Placement(
                        x_mm=posicion_ala_x,
                        y_mm=origen_y_mm,
                        z_mm=origen_z_mm,
                    )
                )

            elif nombre.startswith(
                ("estabilizador horizontal", "horizontal stabilizer")
            ):
                objeto.establecer_placement(
                    Placement(
                        x_mm=posicion_cola_x,
                        y_mm=origen_y_mm,
                        z_mm=posicion_horizontal_z,
                    )
                )

            elif nombre.startswith(
                ("estabilizador vertical", "vertical stabilizer")
            ):
                objeto.establecer_placement(
                    Placement(
                        x_mm=posicion_vertical_x,
                        y_mm=origen_y_mm,
                        z_mm=posicion_vertical_z,
                        roll_deg=90.0,
                    )
                )

        # -----------------------------------------------------
        # Ordenar góndolas
        # -----------------------------------------------------

        gondolas = [
            objeto
            for objeto
            in self.aplicacion.documento.objetos
            if isinstance(
                objeto,
                NacelleComponent,
            )
        ]

        posicion_gondola_x = (
            origen_x_mm
            + 0.30 * longitud_mm
        )

        separacion_base_y = max(
            0.52 * semienvergadura_mm,
            0.85 * ancho_mm,
        )

        for indice, gondola in enumerate(gondolas):
            numero_par = indice // 2

            if indice % 2 == 0:
                lado = 1.0
            else:
                lado = -1.0

            separacion_adicional = (
                numero_par
                * 0.22
                * semienvergadura_mm
            )

            posicion_y = (
                origen_y_mm
                + lado
                * (
                    separacion_base_y
                    + separacion_adicional
                )
            )

            diametro_gondola = float(
                gondola.parametros.max_diameter_mm
            )

            posicion_z = (
                origen_z_mm
                - 0.30 * altura_mm
                - 0.55 * diametro_gondola
            )

            gondola.establecer_placement(
                Placement(
                    x_mm=posicion_gondola_x,
                    y_mm=posicion_y,
                    z_mm=posicion_z,
                )
            )
    def ordenar_componentes(self):
        """
        Reorganiza manualmente los componentes principales
        alrededor del fuselaje de referencia.
        """

        try:
            self._ordenar_componentes_automaticamente()

            errores = (
                self.aplicacion
                .recalcular_documento()
            )

            if errores:
                mensajes = [
                    error["mensaje"]
                    for error in errores
                ]

                raise RuntimeError(
                    "\n".join(mensajes)
                )

            objeto_seleccionado = (
                self.objeto_actual
            )

            self.arbol_documento.actualizar()

            if objeto_seleccionado is not None:
                self.arbol_documento.seleccionar_objeto(
                    objeto_seleccionado.id
                )
            elif self.aplicacion.documento.objetos:
                primer_objeto = (
                    self.aplicacion.documento.objetos[0]
                )

                self.arbol_documento.seleccionar_objeto(
                    primer_objeto.id
                )

            self.statusBar().showMessage(
                "Components arranged automatically.",
                4000,
            )

        except Exception as error:
            QMessageBox.critical(
                self,
                "Unable to arrange components",
                display_error(error),
            )

    def crear_nueva_ala(self):
        """Crea un nuevo componente de tipo ala."""

        try:
            cantidad_alas = sum(
                isinstance(objeto, WingComponent)
                for objeto
                in self.aplicacion.documento.objetos
            )

            if cantidad_alas == 0:
                nombre = "Main wing"
            else:
                nombre = f"Wing {cantidad_alas + 1}"

            componente = (
                self.aplicacion.crear_componente(
                    clave="wing",
                    nombre=nombre,
                )
            )
            self._ordenar_componentes_automaticamente()
            errores = (
                self.aplicacion
                .recalcular_documento()
            )

            if errores:
                mensajes = [
                    error["mensaje"]
                    for error in errores
                ]
                raise RuntimeError(
                    "\n".join(mensajes)
                )

            self.arbol_documento.actualizar()
            self.arbol_documento.seleccionar_objeto(
                componente.id
            )

        except Exception as error:
            QMessageBox.critical(
                self,
                "Unable to create component",
                display_error(error),
            )

    def crear_nuevo_fuselaje(self):
        """Crea un nuevo componente de tipo fuselaje."""

        try:
            cantidad = sum(
                isinstance(objeto, FuselageComponent)
                for objeto in self.aplicacion.documento.objetos
            )

            if cantidad == 0:
                nombre = "Main fuselage"
            else:
                nombre = f"Fuselage {cantidad + 1}"

            componente = self.aplicacion.crear_componente(
                clave="fuselage",
                nombre=nombre,
            )
            self._ordenar_componentes_automaticamente()
            errores = self.aplicacion.recalcular_documento()

            if errores:
                mensajes = [
                    error["mensaje"]
                    for error in errores
                ]
                raise RuntimeError("\n".join(mensajes))

            self.arbol_documento.actualizar()
            self.arbol_documento.seleccionar_objeto(
                componente.id
            )

        except Exception as error:
            QMessageBox.critical(
                self,
                "Unable to create fuselage",
                display_error(error),
            )
    def crear_estabilizador_horizontal(self):
        """Crea un estabilizador horizontal paramétrico."""

        try:
            cantidad = sum(
                objeto.nombre.startswith(
                    ("Estabilizador horizontal", "Horizontal stabilizer")
                )
                for objeto in self.aplicacion.documento.objetos
            )

            if cantidad == 0:
                nombre = "Horizontal stabilizer"
            else:
                nombre = (
                    f"Horizontal stabilizer {cantidad + 1}"
                )

            componente = self.aplicacion.crear_componente(
                clave="wing",
                nombre=nombre,
            )

            componente.establecer_modo_superficie(
                "simetrica"
            )

            componente.actualizar_parametros(
                perfil_raiz="0012",
                perfil_punta="0012",
                cuerda_raiz_mm=500.0,
                cuerda_punta_mm=250.0,
                semi_span_mm=1500.0,
                flecha_grados=25.0,
                diedro_grados=0.0,
                torsion_punta_grados=0.0,
                numero_puntos=60,
                numero_secciones=10,
            )

            componente.establecer_placement(
                Placement(
                    x_mm=6200.0,
                    y_mm=0.0,
                    z_mm=0.0,
                )
            )
            self._ordenar_componentes_automaticamente()
            errores = self.aplicacion.recalcular_documento()

            if errores:
                mensajes = [
                    error["mensaje"]
                    for error in errores
                ]
                raise RuntimeError("\n".join(mensajes))

            self.arbol_documento.actualizar()
            self.arbol_documento.seleccionar_objeto(
                componente.id
            )

        except Exception as error:
            QMessageBox.critical(
                self,
                "Unable to create horizontal stabilizer",
                display_error(error),
            )

    def crear_estabilizador_vertical(self):
        """Crea un estabilizador vertical paramétrico."""

        try:
            cantidad = sum(
                objeto.nombre.startswith(
                    ("Estabilizador vertical", "Vertical stabilizer")
                )
                for objeto in self.aplicacion.documento.objetos
            )

            if cantidad == 0:
                nombre = "Vertical stabilizer"
            else:
                nombre = (
                    f"Vertical stabilizer {cantidad + 1}"
                )

            componente = self.aplicacion.crear_componente(
                clave="wing",
                nombre=nombre,
            )

            componente.establecer_modo_superficie(
                "semiala_positiva"
            )

            componente.actualizar_parametros(
                perfil_raiz="0012",
                perfil_punta="0012",
                cuerda_raiz_mm=600.0,
                cuerda_punta_mm=220.0,
                semi_span_mm=1200.0,
                flecha_grados=30.0,
                diedro_grados=0.0,
                torsion_punta_grados=0.0,
                numero_puntos=60,
                numero_secciones=10,
            )

            componente.establecer_placement(
                Placement(
                    x_mm=6200.0,
                    y_mm=0.0,
                    z_mm=500.0,
                    roll_deg=90.0,
                )
            )
            self._ordenar_componentes_automaticamente()
            errores = self.aplicacion.recalcular_documento()

            if errores:
                mensajes = [
                    error["mensaje"]
                    for error in errores
                ]
                raise RuntimeError("\n".join(mensajes))

            self.arbol_documento.actualizar()
            self.arbol_documento.seleccionar_objeto(
                componente.id
            )

        except Exception as error:
            QMessageBox.critical(
                self,
                "Unable to create vertical stabilizer",
                display_error(error),
            )
    def crear_nueva_gondola(self):
        """Crea una nueva góndola paramétrica."""

        try:
            gondolas = [
                objeto
                for objeto
                in self.aplicacion.documento.objetos
                if isinstance(objeto, NacelleComponent)
            ]

            numero = len(gondolas) + 1
            nombre = f"Nacelle {numero}"

            componente = (
                self.aplicacion.crear_componente(
                    clave="nacelle",
                    nombre=nombre,
                )
            )

            self._ordenar_componentes_automaticamente()

            errores = (
                self.aplicacion
                .recalcular_documento()
            )

            if errores:
                mensajes = [
                    error["mensaje"]
                    for error in errores
                ]
                raise RuntimeError(
                    "\n".join(mensajes)
                )

            self.arbol_documento.actualizar()
            self.arbol_documento.seleccionar_objeto(
                componente.id
            )

        except Exception as error:
            QMessageBox.critical(
                self,
                "Unable to create nacelle",
                display_error(error),
            )

    def recalcular_objeto_actual(self):
        """Aplica los valores del editor al objeto actual."""

        if self.objeto_actual is None:
            QMessageBox.warning(
                self,
                "No selection",
                "Select an object in the document.",
            )
            return

        try:
            if isinstance(
                self.objeto_actual,
                WingComponent,
            ):
                nombre = (
                    self.panel_ala.leer_nombre()
                )
                parametros = (
                    self.panel_ala.leer_parametros()
                )
                densidad = (
                    self.panel_ala.leer_densidad()
                )
                modelo_masa = (
                    self.panel_ala.leer_modelo_masa()
                )
                espesor_mm = (
                    self.panel_ala.leer_espesor()
                )

                self.objeto_actual.establecer_nombre(
                    nombre
                )
                self.objeto_actual.establecer_parametros(
                    parametros
                )
                self.objeto_actual.establecer_densidad(
                    densidad
                )
                self.objeto_actual.establecer_modelo_masa(
                    modelo_masa,
                    espesor_mm,
                )

            elif isinstance(
                self.objeto_actual,
                FuselageComponent,
            ):
                nombre = (
                    self.panel_fuselaje.leer_nombre()
                )
                parametros = (
                    self.panel_fuselaje.leer_parametros()
                )
                densidad = (
                    self.panel_fuselaje.leer_densidad()
                )
                modelo_masa = (
                    self.panel_fuselaje.leer_modelo_masa()
                )
                espesor_mm = (
                    self.panel_fuselaje.leer_espesor()
                )

                self.objeto_actual.establecer_nombre(
                    nombre
                )
                self.objeto_actual.establecer_parametros(
                    parametros
                )
                self.objeto_actual.establecer_densidad(
                    densidad
                )
                self.objeto_actual.establecer_modelo_masa(
                    modelo_masa,
                    espesor_mm,
                )

            elif isinstance(
                self.objeto_actual,
                NacelleComponent,
            ):
                nombre = (
                    self.panel_gondola.leer_nombre()
                )
                parametros = (
                    self.panel_gondola.leer_parametros()
                )
                densidad = (
                    self.panel_gondola.leer_densidad()
                )
                modelo_masa = (
                    self.panel_gondola.leer_modelo_masa()
                )
                espesor_mm = (
                    self.panel_gondola.leer_espesor()
                )

                self.objeto_actual.establecer_nombre(
                    nombre
                )
                self.objeto_actual.establecer_parametros(
                    parametros
                )
                self.objeto_actual.establecer_densidad(
                    densidad
                )
                self.objeto_actual.establecer_modelo_masa(
                    modelo_masa,
                    espesor_mm,
                )

            errores = (
                self.aplicacion
                .recalcular_documento()
            )

            if errores:
                mensajes = [
                    error["mensaje"]
                    for error in errores
                ]
                raise RuntimeError(
                    "\n".join(mensajes)
                )

            self.arbol_documento.actualizar()
            self.arbol_documento.seleccionar_objeto(
                self.objeto_actual.id
            )

        except Exception as error:
            self.arbol_documento.actualizar()

            QMessageBox.critical(
                self,
                "Unable to rebuild",
                display_error(error),
            )

    def eliminar_objeto_actual(self):
        """Elimina el objeto seleccionado."""

        if self.objeto_actual is None:
            QMessageBox.warning(
                self,
                "No selection",
                "Select an object to delete.",
            )
            return

        respuesta = QMessageBox.question(
            self,
            "Delete object",
            (
                f"Do you want to delete "
                f"'{self.objeto_actual.nombre}'?"
            ),
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if respuesta != QMessageBox.StandardButton.Yes:
            return

        identificador = self.objeto_actual.id

        self.aplicacion.documento.eliminar_objeto(
            identificador
        )

        self.objeto_actual = None
        self.actor_cg = None

        self.editores_componentes.setCurrentWidget(
            self.panel_sin_objeto
        )
        self.panel_placement.limpiar()
        self.boton_exportar.setEnabled(False)

        self.arbol_documento.actualizar()
        self._actualizar_escena_documento()

        self.etiqueta_resultados.setText(
            "Object deleted."
        )

    def _seleccionar_objeto(
        self,
        identificador,
    ):
        """Selecciona un objeto del árbol."""

        objeto = (
            self.aplicacion.documento
            .obtener_objeto(identificador)
        )

        if objeto is None:
            return

        self.objeto_actual = objeto

        self.panel_placement.establecer_placement(
            objeto.placement
        )
        self.panel_placement.habilitar(True)

        if isinstance(objeto, WingComponent):
            self.panel_ala.establecer_componente(
                objeto
            )
            self.editores_componentes.setCurrentWidget(
                self.panel_ala
            )

            self._mostrar_resultados_ala(
                objeto
            )

        elif isinstance(objeto, FuselageComponent):
            self.panel_fuselaje.establecer_componente(
                objeto
            )
            self.editores_componentes.setCurrentWidget(
                self.panel_fuselaje
            )

            self._mostrar_resultados_fuselaje(
                objeto
            )

        elif isinstance(objeto, NacelleComponent):
            self.panel_gondola.establecer_componente(
                objeto
            )
            self.editores_componentes.setCurrentWidget(
                self.panel_gondola
            )

            self._mostrar_resultados_gondola(
                objeto
            )

        self.boton_exportar.setEnabled(
            objeto.shape is not None
            and objeto.valido
        )

        self._actualizar_escena_documento()

    def aplicar_placement_objeto_actual(
        self,
        placement,
    ):
        """Aplica posición y orientación al objeto seleccionado."""

        if self.objeto_actual is None:
            QMessageBox.warning(
                self,
                "No selection",
                "Select an object in the document.",
            )
            self.panel_placement.limpiar()
            return

        try:
            identificador = self.objeto_actual.id

            self.objeto_actual.establecer_placement(
                placement
            )

            errores = (
                self.aplicacion
                .recalcular_documento()
            )

            if errores:
                mensajes = [
                    error["mensaje"]
                    for error in errores
                ]
                raise RuntimeError(
                    "\n".join(mensajes)
                )

            self.arbol_documento.actualizar()
            self.arbol_documento.seleccionar_objeto(
                identificador
            )

            if isinstance(
                self.objeto_actual,
                WingComponent,
            ):
                self._mostrar_resultados_ala(
                    self.objeto_actual
                )

            elif isinstance(
                self.objeto_actual,
                FuselageComponent,
            ):
                self._mostrar_resultados_fuselaje(
                    self.objeto_actual
                )

            self._actualizar_escena_documento()

        except Exception as error:
            QMessageBox.critical(
                self,
                "Placement error",
                display_error(error),
            )

            if self.objeto_actual is not None:
                self.panel_placement.establecer_placement(
                    self.objeto_actual.placement
                )

    def _cambiar_visibilidad(
        self,
        identificador,
        visible,
    ):
        """Cambia la visibilidad de un objeto."""

        objeto = (
            self.aplicacion.documento
            .obtener_objeto(identificador)
        )

        if objeto is None:
            return

        objeto.establecer_visibilidad(
            visible
        )

        actor = self.actores_objetos.get(
            identificador
        )

        if actor is not None:
            actor.SetVisibility(visible)

        if (
            objeto is self.objeto_actual
            and self.actor_cg is not None
        ):
            self.actor_cg.SetVisibility(
                visible
            )

        self._actualizar_limites()
        self.visualizador.GetRenderWindow().Render()

    def _mostrar_resultados_ala(
        self,
        componente,
    ):
        """Muestra resultados de la superficie seleccionada."""

        propiedades = componente.propiedades

        if propiedades is None:
            self.etiqueta_resultados.setText(
                "This object has no results yet."
            )
            return

        area_planta = (
            componente.parametros
            .superficie_aproximada_mm2
            / 1_000_000.0
        )

        if propiedades.modelo_masa == "carcasa":
            modelo_texto = "Shell"
            detalle_espesor = (
                f"Thickness: "
                f"{propiedades.espesor_mm:.2f} mm\n"
            )
            etiqueta_volumen = (
                "Material volume"
            )
        else:
            modelo_texto = "Solid"
            detalle_espesor = ""
            etiqueta_volumen = (
                "Solid volume"
            )

        self.etiqueta_resultados.setText(
            f"Name: {componente.nombre}\n"
            f"Type: {display_label(componente.tipo)}\n"
            f"Valid: "
            f"{componente.valido}\n\n"

            f"Planform area: "
            f"{area_planta:.3f} m²\n"

            f"Surface area: "
            f"{propiedades.area_superficial_m2:.3f} m²\n"

            f"Mass model: "
            f"{modelo_texto}\n"

            f"{detalle_espesor}"

            f"{etiqueta_volumen}: "
            f"{propiedades.volumen_m3:.6f} m³\n"

            f"Density: "
            f"{propiedades.densidad_kg_m3:.1f} kg/m³\n"

            f"Estimated mass: "
            f"{propiedades.masa_kg:.3f} kg\n\n"

            "Center of gravity:\n"
            f"X = {propiedades.cg_x_mm:.2f} mm\n"
            f"Y = {propiedades.cg_y_mm:.2f} mm\n"
            f"Z = {propiedades.cg_z_mm:.2f} mm\n\n"

            "Moments of inertia:\n"
            f"Ixx = "
            f"{propiedades.inercia_xx_kg_m2:.3f} kg·m²\n"
            f"Iyy = "
            f"{propiedades.inercia_yy_kg_m2:.3f} kg·m²\n"
            f"Izz = "
            f"{propiedades.inercia_zz_kg_m2:.3f} kg·m²"
        )

    def _mostrar_resultados_fuselaje(
        self,
        componente,
    ):
        """Muestra resultados del fuselaje seleccionado."""

        propiedades = componente.propiedades

        if propiedades is None:
            self.etiqueta_resultados.setText(
                "This object has no results yet."
            )
            return

        parametros = componente.parametros

        if propiedades.modelo_masa == "carcasa":
            modelo_texto = "Shell"
            detalle_espesor = (
                f"Thickness: "
                f"{propiedades.espesor_mm:.2f} mm\n"
            )
            etiqueta_volumen = (
                "Material volume"
            )
        else:
            modelo_texto = "Solid"
            detalle_espesor = ""
            etiqueta_volumen = (
                "Solid volume"
            )

        self.etiqueta_resultados.setText(
            f"Name: {componente.nombre}\n"
            f"Type: {display_label(componente.tipo)}\n"
            f"Valid: "
            f"{componente.valido}\n\n"

            f"Length: "
            f"{parametros.length_mm:.2f} mm\n"

            f"Maximum width: "
            f"{parametros.max_width_mm:.2f} mm\n"

            f"Maximum height: "
            f"{parametros.max_height_mm:.2f} mm\n\n"

            f"Surface area: "
            f"{propiedades.area_superficial_m2:.3f} m²\n"

            f"Mass model: "
            f"{modelo_texto}\n"

            f"{detalle_espesor}"

            f"{etiqueta_volumen}: "
            f"{propiedades.volumen_m3:.6f} m³\n"

            f"Density: "
            f"{propiedades.densidad_kg_m3:.1f} kg/m³\n"

            f"Estimated mass: "
            f"{propiedades.masa_kg:.3f} kg\n\n"

            "Center of gravity:\n"
            f"X = {propiedades.cg_x_mm:.2f} mm\n"
            f"Y = {propiedades.cg_y_mm:.2f} mm\n"
            f"Z = {propiedades.cg_z_mm:.2f} mm\n\n"

            "Moments of inertia:\n"
            f"Ixx = "
            f"{propiedades.inercia_xx_kg_m2:.3f} kg·m²\n"
            f"Iyy = "
            f"{propiedades.inercia_yy_kg_m2:.3f} kg·m²\n"
            f"Izz = "
            f"{propiedades.inercia_zz_kg_m2:.3f} kg·m²"
        )
    def _mostrar_resultados_gondola(
        self,
        componente,
    ):
        """Muestra los resultados de la góndola seleccionada."""

        propiedades = componente.propiedades

        if propiedades is None:
            self.etiqueta_resultados.setText(
                "This nacelle has no results yet."
            )
            return

        parametros = componente.parametros

        if propiedades.modelo_masa == "carcasa":
            modelo_texto = "Approximate shell"
            detalle_espesor = (
                f"Mass-model thickness: "
                f"{propiedades.espesor_mm:.2f} mm\n"
            )
            etiqueta_volumen = (
                "Approximate material volume"
            )
        else:
            modelo_texto = "Actual wall volume"
            detalle_espesor = (
                f"Geometric thickness: "
                f"{parametros.wall_thickness_mm:.2f} mm\n"
            )
            etiqueta_volumen = (
                "Actual material volume"
            )

        self.etiqueta_resultados.setText(
            f"Name: {componente.nombre}\n"
            f"Type: {display_label(componente.tipo)}\n"
            f"Valid: "
            f"{componente.valido}\n\n"

            f"Length: "
            f"{parametros.length_mm:.2f} mm\n"

            f"Inlet diameter: "
            f"{parametros.inlet_diameter_mm:.2f} mm\n"

            f"Maximum diameter: "
            f"{parametros.max_diameter_mm:.2f} mm\n"

            f"Outlet diameter: "
            f"{parametros.outlet_diameter_mm:.2f} mm\n"

            f"Wall thickness: "
            f"{parametros.wall_thickness_mm:.2f} mm\n"

            f"Maximum-diameter station: "
            f"{parametros.max_diameter_position_ratio * 100.0:.1f} %\n\n"

            f"Surface area: "
            f"{propiedades.area_superficial_m2:.3f} m²\n"

            f"Mass model: "
            f"{modelo_texto}\n"

            f"{detalle_espesor}"

            f"{etiqueta_volumen}: "
            f"{propiedades.volumen_m3:.6f} m³\n"

            f"Density: "
            f"{propiedades.densidad_kg_m3:.1f} kg/m³\n"

            f"Estimated mass: "
            f"{propiedades.masa_kg:.3f} kg\n\n"

            "Center of gravity:\n"
            f"X = {propiedades.cg_x_mm:.2f} mm\n"
            f"Y = {propiedades.cg_y_mm:.2f} mm\n"
            f"Z = {propiedades.cg_z_mm:.2f} mm\n\n"

            "Moments of inertia:\n"
            f"Ixx = "
            f"{propiedades.inercia_xx_kg_m2:.3f} kg·m²\n"
            f"Iyy = "
            f"{propiedades.inercia_yy_kg_m2:.3f} kg·m²\n"
            f"Izz = "
            f"{propiedades.inercia_zz_kg_m2:.3f} kg·m²"
        )
    def _crear_actor_geometria(
        self,
        objeto,
    ):
        """Convierte un objeto CAD en un actor VTK."""

        malla = convertir_shape_a_vtk(
            objeto.shape,
            tolerancia=2.0,
        )

        if malla.GetNumberOfPoints() == 0:
            return None

        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(malla)
        mapper.ScalarVisibilityOff()

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)

        propiedad = actor.GetProperty()

        if objeto is self.objeto_actual:
            propiedad.SetColor(
                0.95,
                0.75,
                0.25,
            )
        else:
            propiedad.SetColor(
                0.82,
                0.86,
                0.94,
            )

        propiedad.SetRepresentationToSurface()
        propiedad.SetInterpolationToPhong()
        propiedad.SetAmbient(0.30)
        propiedad.SetDiffuse(0.70)
        propiedad.SetSpecular(0.25)
        propiedad.SetSpecularPower(20.0)

        if self.boton_aristas.isChecked():
            propiedad.EdgeVisibilityOn()
        else:
            propiedad.EdgeVisibilityOff()

        actor.SetVisibility(
            objeto.visible
        )

        return actor

    def _actualizar_escena_documento(self):
        """Dibuja los objetos y centros de gravedad."""

        self.renderer.RemoveAllViewProps()
        self.actores_objetos.clear()

        self.actor_cg = None
        self.actor_cg_global = None

        for objeto in self.aplicacion.documento.objetos:
            if (
                objeto.shape is None
                or not objeto.valido
            ):
                continue

            actor = self._crear_actor_geometria(
                objeto
            )

            if actor is None:
                continue

            self.renderer.AddActor(actor)

            self.actores_objetos[
                objeto.id
            ] = actor

        # Estos límites se calculan antes de agregar
        # las esferas para que no alteren el encuadre.
        self._actualizar_limites()

        # Centro de gravedad del ensamblaje completo.
        try:
            propiedades_globales = (
                self.aplicacion.documento
                .calcular_propiedades_globales()
            )

            if (
                propiedades_globales["masa_total_kg"]
                > 0.0
            ):
                self._mostrar_centro_gravedad_global(
                    propiedades_globales
                )

        except Exception:
            self.actor_cg_global = None

        # Centro de gravedad del objeto seleccionado.
        if (
            self.objeto_actual is not None
            and self.objeto_actual.visible
            and getattr(
                self.objeto_actual,
                "propiedades",
                None,
            ) is not None
        ):
            self._mostrar_centro_gravedad(
                self.objeto_actual.propiedades
            )

        self.vista_isometrica()

    def _actualizar_limites(self):
        """Actualiza los límites de la escena."""

        limites = (
            self.renderer.ComputeVisiblePropBounds()
        )

        if (
            limites is None
            or limites[0] > limites[1]
        ):
            self.limites_modelo = None
        else:
            self.limites_modelo = limites

    def _mostrar_centro_gravedad(
        self,
        propiedades,
    ):
        """Muestra el CG del objeto seleccionado."""

        if self.limites_modelo is None:
            return

        limites = self.limites_modelo

        tamano = max(
            limites[1] - limites[0],
            limites[3] - limites[2],
            limites[5] - limites[4],
        )

        esfera = vtk.vtkSphereSource()
        esfera.SetCenter(
            propiedades.cg_x_mm,
            propiedades.cg_y_mm,
            propiedades.cg_z_mm,
        )
        esfera.SetRadius(
            0.012 * tamano
        )
        esfera.SetThetaResolution(30)
        esfera.SetPhiResolution(30)

        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(
            esfera.GetOutputPort()
        )

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(
            1.0,
            0.15,
            0.10,
        )

        self.renderer.AddActor(actor)
        self.actor_cg = actor
    def _mostrar_centro_gravedad_global(
        self,
        propiedades_globales,
    ):
        """Muestra el CG global mediante una esfera verde."""

        if self.limites_modelo is None:
            return

        limites = self.limites_modelo

        tamano = max(
            limites[1] - limites[0],
            limites[3] - limites[2],
            limites[5] - limites[4],
        )

        if tamano <= 0.0:
            return

        esfera = vtk.vtkSphereSource()
        esfera.SetCenter(
            propiedades_globales["cg_x_mm"],
            propiedades_globales["cg_y_mm"],
            propiedades_globales["cg_z_mm"],
        )
        esfera.SetRadius(
            0.016 * tamano
        )
        esfera.SetThetaResolution(36)
        esfera.SetPhiResolution(36)

        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(
            esfera.GetOutputPort()
        )

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)

        propiedad = actor.GetProperty()
        propiedad.SetColor(
            0.10,
            0.95,
            0.25,
        )
        propiedad.SetAmbient(0.35)
        propiedad.SetDiffuse(0.65)
        propiedad.SetSpecular(0.35)
        propiedad.SetSpecularPower(25.0)

        self.renderer.AddActor(actor)
        self.actor_cg_global = actor
    def _aplicar_vista(
        self,
        direccion,
        vector_arriba,
        proyeccion_paralela=False,
    ):
        """Configura la cámara."""

        if self.limites_modelo is None:
            self.visualizador.GetRenderWindow().Render()
            return

        limites = self.limites_modelo

        centro = (
            0.5 * (limites[0] + limites[1]),
            0.5 * (limites[2] + limites[3]),
            0.5 * (limites[4] + limites[5]),
        )

        tamano = max(
            limites[1] - limites[0],
            limites[3] - limites[2],
            limites[5] - limites[4],
        )

        camara = self.renderer.GetActiveCamera()

        camara.SetFocalPoint(*centro)
        camara.SetPosition(
            centro[0] + direccion[0] * tamano,
            centro[1] + direccion[1] * tamano,
            centro[2] + direccion[2] * tamano,
        )
        camara.SetViewUp(*vector_arriba)

        if proyeccion_paralela:
            camara.ParallelProjectionOn()
        else:
            camara.ParallelProjectionOff()

        self.renderer.ResetCamera()
        self.renderer.ResetCameraClippingRange()
        self.visualizador.GetRenderWindow().Render()

    def vista_isometrica(self):
        self._aplicar_vista(
            (-1.2, -1.4, 0.8),
            (0.0, 0.0, 1.0),
            False,
        )

    def vista_superior(self):
        self._aplicar_vista(
            (0.0, 0.0, 2.0),
            (0.0, 1.0, 0.0),
            True,
        )

    def vista_frontal(self):
        self._aplicar_vista(
            (-2.0, 0.0, 0.0),
            (0.0, 0.0, 1.0),
            True,
        )

    def vista_lateral(self):
        self._aplicar_vista(
            (0.0, -2.0, 0.0),
            (0.0, 0.0, 1.0),
            True,
        )

    def ajustar_vista(self):
        if not self.actores_objetos:
            return

        self.renderer.ResetCamera()
        self.renderer.ResetCameraClippingRange()
        self.visualizador.GetRenderWindow().Render()

    def alternar_aristas(
        self,
        activado,
    ):
        for actor in self.actores_objetos.values():
            if activado:
                actor.GetProperty().EdgeVisibilityOn()
            else:
                actor.GetProperty().EdgeVisibilityOff()

        self.visualizador.GetRenderWindow().Render()
    def mostrar_propiedades_globales(self):
        """
        Muestra las propiedades físicas del ensamblaje completo.
        """

        try:
            resultado = (
                self.aplicacion.documento
                .calcular_propiedades_globales()
            )

            componentes = resultado["componentes"]

            if not componentes:
                QMessageBox.warning(
                    self,
                    "No properties",
                    (
                        "There are no valid components "
                        "with physical properties."
                    ),
                )
                return

            lineas_componentes = []

            for componente in componentes:
                lineas_componentes.append(
                    (
                        f"- {componente['nombre']} "
                        f"[{display_label(componente['tipo'])}]: "
                        f"{componente['masa_kg']:.3f} kg"
                    )
                )

            desglose = "\n".join(
                lineas_componentes
            )

            mensaje = (
                "GLOBAL MODEL PROPERTIES\n\n"
                f"Total mass: "
                f"{resultado['masa_total_kg']:.3f} kg\n\n"
                "Global center of gravity:\n"
                f"X = {resultado['cg_x_mm']:.2f} mm\n"
                f"Y = {resultado['cg_y_mm']:.2f} mm\n"
                f"Z = {resultado['cg_z_mm']:.2f} mm\n\n"
                "Moments of inertia about the global CG:\n"
                f"Ixx = "
                f"{resultado['inercia_xx_kg_m2']:.3f} "
                "kg*m^2\n"
                f"Iyy = "
                f"{resultado['inercia_yy_kg_m2']:.3f} "
                "kg*m^2\n"
                f"Izz = "
                f"{resultado['inercia_zz_kg_m2']:.3f} "
                "kg*m^2\n\n"
                "Component breakdown:\n"
                f"{desglose}"
            )

            QMessageBox.information(
                self,
                "Global properties",
                mensaje,
            )

        except Exception as error:
            QMessageBox.critical(
                self,
                "Global properties error",
                display_error(error),
            )

    def _elegir_archivo_exportacion(self, sugerido, titulo):
        """Select format and confirm the final filename before overwriting."""
        archivo, filtro = QFileDialog.getSaveFileName(
            self,
            titulo,
            str(sugerido.with_suffix("")),
            ";;".join(EXPORT_FILTERS),
            options=QFileDialog.Option.DontUseNativeDialog,
        )
        if not archivo:
            return None
        extension = EXPORT_FILTERS.get(filtro, "step")
        ruta = Path(archivo)
        permitidas = (".step", ".stp") if extension == "step" else ("." + extension,)
        if ruta.suffix.lower() not in permitidas:
            ruta = ruta.with_suffix("." + extension)
            if ruta.exists():
                respuesta = QMessageBox.question(
                    self, "Replace file?",
                    f"The file already exists:\n{ruta}\n\nReplace it?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if respuesta != QMessageBox.StandardButton.Yes:
                    return None
        return ruta

    def exportar_objeto(self):
        """Exporta el objeto seleccionado en el formato elegido."""

        if (
            self.objeto_actual is None
            or self.objeto_actual.shape is None
            or not self.objeto_actual.valido
        ):
            QMessageBox.warning(
                self,
                "No geometry",
                "Select a valid object.",
            )
            return

        carpeta = (
            Path(__file__).resolve().parents[1]
            / "exports"
        )
        carpeta.mkdir(
            parents=True,
            exist_ok=True,
        )

        nombre_archivo = (
            self.objeto_actual.nombre
            .strip()
            .replace(" ", "_")
        )

        archivo_sugerido = (
            carpeta
            / f"{nombre_archivo}.step"
        )

        try:
            archivo = self._elegir_archivo_exportacion(
                archivo_sugerido, "Export selected object"
            )
            if archivo is None:
                return
            ruta = exportar_geometria(
                self.objeto_actual.shape,
                archivo,
                self.objeto_actual.nombre,
            )

            QMessageBox.information(
                self,
                "Export complete",
                f"File saved to:\n{ruta}",
            )

        except Exception as error:
            QMessageBox.critical(
                self,
                "Export error",
                display_error(error),
            )
    def exportar_proyecto_completo(self):
        """Exporta todos los componentes válidos en el formato elegido."""

        try:
            errores = (
                self.aplicacion
                .recalcular_documento()
            )

            if errores:
                mensajes = [
                    error["mensaje"]
                    for error in errores
                ]

                raise RuntimeError(
                    "The project cannot be exported "
                    "because some components have errors:\n\n"
                    + "\n".join(mensajes)
                )

            geometrias = []
            nombres = []

            for objeto in (
                self.aplicacion
                .documento
                .objetos
            ):
                if not objeto.valido:
                    continue

                if objeto.shape is None:
                    continue

                if objeto.shape.IsNull():
                    continue

                geometrias.append(
                    objeto.shape
                )
                nombres.append(objeto.nombre)

            if not geometrias:
                QMessageBox.warning(
                    self,
                    "Project has no geometry",
                    "The project contains no "
                    "valid components to export.",
                )
                return

            carpeta = (
                Path(__file__).resolve().parents[1]
                / "exports"
            )
            carpeta.mkdir(
                parents=True,
                exist_ok=True,
            )

            archivo_sugerido = (
                carpeta
                / "aircraft_multibody.step"
            )

            archivo = self._elegir_archivo_exportacion(
                archivo_sugerido, "Export project"
            )
            if archivo is None:
                return
            ruta, cantidad = exportar_proyecto(
                geometrias,
                archivo,
                nombres,
            )

            QMessageBox.information(
                self,
                "Export complete",
                (
                    f"Project exported successfully.\n\n"
                    f"Components exported: {cantidad}\n"
                    f"File:\n{ruta}"
                ),
            )

        except Exception as error:
            QMessageBox.critical(
                self,
                "Unable to export project",
                display_error(error),
            )
    def closeEvent(self, evento):
        """Cierra correctamente VTK."""

        if self.analysis_panel.busy():
            QMessageBox.information(self, "Analysis running", "Wait for the analysis to finish or cancel the task before closing WingCAD.")
            evento.ignore()
            return
        self.analysis_panel.finalize()
        self.visualizador.Finalize()
        evento.accept()
