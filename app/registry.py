"""Registro de tipos de componentes CAD."""

from collections import OrderedDict
from dataclasses import dataclass

from app.cad_object import CADObject


@dataclass(frozen=True)
class ComponentDefinition:
    """Descripción de un tipo de componente disponible."""

    clave: str
    etiqueta: str
    categoria: str
    clase: type


class ComponentRegistry:
    """Administra los tipos de objetos CAD disponibles."""

    def __init__(self):
        self._definiciones = OrderedDict()

    def registrar(
        self,
        clave,
        clase,
        etiqueta=None,
        categoria="General",
    ):
        """Registra un nuevo tipo de componente."""

        clave = str(clave).strip().lower()

        if not clave:
            raise ValueError(
                "La clave del componente no puede estar vacía."
            )

        if clave in self._definiciones:
            raise ValueError(
                f"El componente '{clave}' ya está registrado."
            )

        if not isinstance(clase, type):
            raise TypeError(
                "El componente registrado debe ser una clase."
            )

        if not issubclass(clase, CADObject):
            raise TypeError(
                "La clase debe heredar de CADObject."
            )

        if etiqueta is None:
            etiqueta = clase.tipo

        definicion = ComponentDefinition(
            clave=clave,
            etiqueta=str(etiqueta),
            categoria=str(categoria),
            clase=clase,
        )

        self._definiciones[clave] = definicion

        return definicion

    def eliminar_registro(self, clave):
        """Elimina un tipo del registro."""

        clave = str(clave).strip().lower()

        if clave not in self._definiciones:
            raise KeyError(
                f"El componente '{clave}' no está registrado."
            )

        return self._definiciones.pop(clave)

    def obtener(self, clave):
        """Obtiene la definición de un componente."""

        clave = str(clave).strip().lower()

        if clave not in self._definiciones:
            raise KeyError(
                f"El componente '{clave}' no está registrado."
            )

        return self._definiciones[clave]

    def crear(self, clave, **argumentos):
        """Crea una instancia de un componente registrado."""

        definicion = self.obtener(clave)

        return definicion.clase(**argumentos)

    def listar(self):
        """Devuelve todos los componentes disponibles."""

        return tuple(self._definiciones.values())

    def contiene(self, clave):
        """Comprueba si existe una clave."""

        return str(clave).strip().lower() in self._definiciones