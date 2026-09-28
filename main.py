"""Punto de entrada de la aplicación WingCAD."""

import os
import sys

os.environ.setdefault("QT_API", "pyside6")

from PySide6.QtWidgets import QApplication

from gui.main_window import MainWindow


def main():
    aplicacion = QApplication(sys.argv)
    aplicacion.setApplicationName("WingCAD")
    aplicacion.setOrganizationName("WingCAD")

    ventana = MainWindow()
    ventana.show()

    return aplicacion.exec()


if __name__ == "__main__":
    sys.exit(main())