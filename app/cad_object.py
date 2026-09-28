from abc import ABC, abstractmethod
from uuid import uuid4

from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.TopoDS import TopoDS_Shape

from geometry.placement import Placement


class CADObject(ABC):
    """
    Clase base de todos los objetos CAD del programa.

    Separa dos conceptos:

    - local_shape: geometría original del componente.
    - shape: geometría colocada dentro del ensamblaje.
    """

    tipo = "Objeto CAD"

    def __init__(
        self,
        nombre: str,
        placement: Placement | None = None,
    ):
        self.id = str(uuid4())
        self.nombre = nombre

        self.local_shape: TopoDS_Shape | None = None
        self.shape: TopoDS_Shape | None = None

        self.placement = placement or Placement()

        self.visible = True
        self.modificado = True
        self.valido = False
        self.error = ""

        self._geometria_modificada = True
        self._placement_modificado = True

    @abstractmethod
    def construir_geometria(self) -> TopoDS_Shape:
        """Construye la geometría local del componente."""
        raise NotImplementedError

    def actualizar_resultados(self):
        """Método opcional para calcular propiedades físicas."""
        return None

    def recalcular(self):
        """
        Reconstruye la geometría solamente cuando sea necesario.
        """

        if not self.modificado and self.shape is not None:
            return self.shape

        try:
            self.error = ""

            if self._geometria_modificada or self.local_shape is None:
                nueva_geometria = self.construir_geometria()

                if (
                    nueva_geometria is None
                    or nueva_geometria.IsNull()
                ):
                    raise RuntimeError(
                        f"{self.nombre}: no se pudo crear la geometría."
                    )

                analizador_local = BRepCheck_Analyzer(
                    nueva_geometria
                )

                if not analizador_local.IsValid():
                    raise RuntimeError(
                        f"{self.nombre}: la geometría local no es válida."
                    )

                self.local_shape = nueva_geometria

            if self.placement.es_identidad():
                self.shape = self.local_shape
            else:
                self.shape = self.placement.aplicar(
                    self.local_shape
                )

            if self.shape is None or self.shape.IsNull():
                raise RuntimeError(
                    f"{self.nombre}: la transformación produjo "
                    "una geometría vacía."
                )

            analizador_final = BRepCheck_Analyzer(self.shape)

            if not analizador_final.IsValid():
                raise RuntimeError(
                    f"{self.nombre}: la geometría transformada "
                    "no es válida."
                )

            self.actualizar_resultados()

            self.valido = True
            self.modificado = False
            self._geometria_modificada = False
            self._placement_modificado = False

            return self.shape

        except Exception as error:
            self.valido = False
            self.error = str(error)
            raise

    def marcar_modificado(self):
        """Indica que cambió la geometría paramétrica."""

        self.modificado = True
        self.valido = False
        self._geometria_modificada = True
        self._placement_modificado = True

    def establecer_placement(self, placement: Placement):
        """Cambia posición y orientación sin reconstruir la geometría local."""

        if not isinstance(placement, Placement):
            raise TypeError(
                "placement debe ser una instancia de Placement."
            )

        placement.validar()

        self.placement = placement
        self.modificado = True
        self.valido = False
        self._placement_modificado = True

    def establecer_nombre(self, nombre: str):
        nombre = nombre.strip()

        if not nombre:
            raise ValueError(
                "El nombre del objeto no puede estar vacío."
            )

        self.nombre = nombre

    def restaurar_id(self, identificador: str):
        """Asigna el ID guardado en un proyecto WingCAD."""

        if (
            not isinstance(identificador, str)
            or not identificador.strip()
        ):
            raise ValueError(
                "El identificador guardado no es válido."
            )

        self.id = identificador.strip()

    def establecer_visibilidad(self, visible: bool):
        self.visible = bool(visible)

    def obtener_resumen(self) -> dict:
        return {
            "id": self.id,
            "nombre": self.nombre,
            "tipo": self.tipo,
            "visible": self.visible,
            "valido": self.valido,
            "modificado": self.modificado,
            "error": self.error,
            "placement": self.placement.como_diccionario(),
        }

    def __repr__(self):
        return (
            f"{self.__class__.__name__}("
            f"nombre={self.nombre!r}, "
            f"tipo={self.tipo!r}, "
            f"valido={self.valido})"
        )