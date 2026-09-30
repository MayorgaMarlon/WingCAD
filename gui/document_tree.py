"""Árbol de objetos del documento CAD."""

from gui.display_text import display_label, display_error

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QBrush
from PySide6.QtWidgets import (
    QTreeWidget,
    QTreeWidgetItem,
)


class DocumentTree(QTreeWidget):
    """Representa la jerarquía de objetos del documento."""

    objeto_seleccionado = Signal(str)

    visibilidad_modificada = Signal(
        str,
        bool,
    )

    def __init__(self, parent=None):
        super().__init__(parent)

        self.documento = None
        self.elemento_raiz = None

        self.setColumnCount(1)
        self.setHeaderLabel("Document")

        self.setAlternatingRowColors(True)
        self.setMinimumHeight(150)

        self.currentItemChanged.connect(
            self._seleccion_cambiada
        )

        self.itemChanged.connect(
            self._elemento_modificado
        )

    def establecer_documento(self, documento):
        """Asigna un documento y reconstruye el árbol."""

        self.documento = documento
        self.actualizar()

    def actualizar(self):
        """Actualiza los elementos mostrados."""

        self.blockSignals(True)
        self.clear()

        if self.documento is None:
            self.blockSignals(False)
            return

        self.elemento_raiz = QTreeWidgetItem(
            [display_label(self.documento.nombre)]
        )

        self.elemento_raiz.setData(
            0,
            Qt.ItemDataRole.UserRole,
            None,
        )

        fuente = self.elemento_raiz.font(0)
        fuente.setBold(True)
        self.elemento_raiz.setFont(0, fuente)

        self.addTopLevelItem(
            self.elemento_raiz
        )

        for objeto in self.documento.objetos:
            self._agregar_objeto(
                objeto
            )

        self.elemento_raiz.setExpanded(True)

        self.blockSignals(False)

    def _agregar_objeto(self, objeto):
        """Agrega un objeto CAD al árbol."""

        texto = (
            f"{objeto.nombre} "
            f"[{display_label(objeto.tipo)}]"
        )

        elemento = QTreeWidgetItem(
            self.elemento_raiz,
            [texto],
        )

        elemento.setData(
            0,
            Qt.ItemDataRole.UserRole,
            objeto.id,
        )

        banderas = elemento.flags()

        banderas |= (
            Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsUserCheckable
        )

        elemento.setFlags(banderas)

        if objeto.visible:
            elemento.setCheckState(
                0,
                Qt.CheckState.Checked,
            )
        else:
            elemento.setCheckState(
                0,
                Qt.CheckState.Unchecked,
            )

        if objeto.error:
            elemento.setForeground(
                0,
                QBrush(QColor("#c62828")),
            )

            elemento.setToolTip(
                0,
                display_error(objeto.error),
            )

        elif objeto.modificado:
            elemento.setForeground(
                0,
                QBrush(QColor("#d17d00")),
            )

            elemento.setToolTip(
                0,
                "The object needs to be rebuilt.",
            )

        elif objeto.valido:
            elemento.setForeground(
                0,
                QBrush(QColor("#1b7f3a")),
            )

            elemento.setToolTip(
                0,
                "Valid geometry.",
            )

    def _seleccion_cambiada(
        self,
        elemento_actual,
        elemento_anterior,
    ):
        """Emite el identificador del objeto seleccionado."""

        if elemento_actual is None:
            return

        identificador = elemento_actual.data(
            0,
            Qt.ItemDataRole.UserRole,
        )

        if identificador:
            self.objeto_seleccionado.emit(
                identificador
            )

    def _elemento_modificado(
        self,
        elemento,
        columna,
    ):
        """Procesa cambios de visibilidad."""

        if self.documento is None:
            return

        identificador = elemento.data(
            0,
            Qt.ItemDataRole.UserRole,
        )

        if not identificador:
            return

        objeto = self.documento.obtener_objeto(
            identificador
        )

        if objeto is None:
            return

        visible = (
            elemento.checkState(0)
            == Qt.CheckState.Checked
        )

        objeto.establecer_visibilidad(
            visible
        )

        self.visibilidad_modificada.emit(
            identificador,
            visible,
        )

    def seleccionar_objeto(self, identificador):
        """Selecciona un objeto mediante su identificador."""

        if self.elemento_raiz is None:
            return

        for indice in range(
            self.elemento_raiz.childCount()
        ):
            elemento = self.elemento_raiz.child(
                indice
            )

            identificador_elemento = elemento.data(
                0,
                Qt.ItemDataRole.UserRole,
            )

            if identificador_elemento == identificador:
                self.setCurrentItem(
                    elemento
                )
                return