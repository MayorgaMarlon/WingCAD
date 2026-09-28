"""Construcción geométrica de una góndola aeronáutica."""

from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
from OCP.BRepBuilderAPI import (
    BRepBuilderAPI_MakeEdge,
    BRepBuilderAPI_MakeWire,
)
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepOffsetAPI import (
    BRepOffsetAPI_ThruSections,
)
from OCP.gp import (
    gp_Ax2,
    gp_Circ,
    gp_Dir,
    gp_Pnt,
)

from core.nacelle_parameters import (
    NacelleParameters,
)


class NacelleBuilder:
    """
    Construye una góndola hueca mediante dos lofts.

    El loft interior se sustrae del exterior para producir
    una geometría abierta en la entrada y en la salida.
    """

    def __init__(
        self,
        parametros: NacelleParameters,
    ):
        if not isinstance(
            parametros,
            NacelleParameters,
        ):
            raise TypeError(
                "parametros debe ser NacelleParameters."
            )

        parametros.validar()
        self.parametros = parametros

    @staticmethod
    def _suavizado(valor: float) -> float:
        """
        Función smoothstep para transiciones suaves.
        """

        valor = max(
            0.0,
            min(1.0, float(valor)),
        )

        return (
            valor
            * valor
            * (3.0 - 2.0 * valor)
        )

    def _radio_exterior(
        self,
        posicion_relativa: float,
    ) -> float:
        """
        Calcula el radio exterior en una posición
        longitudinal entre 0 y 1.
        """

        p = self.parametros

        posicion_relativa = max(
            0.0,
            min(1.0, posicion_relativa),
        )

        posicion_maxima = (
            p.max_diameter_position_ratio
        )

        if posicion_relativa <= posicion_maxima:
            proporcion = (
                posicion_relativa
                / posicion_maxima
            )

            proporcion = self._suavizado(
                proporcion
            )

            return (
                p.inlet_radius_mm
                + (
                    p.max_radius_mm
                    - p.inlet_radius_mm
                )
                * proporcion
            )

        proporcion = (
            posicion_relativa
            - posicion_maxima
        ) / (
            1.0
            - posicion_maxima
        )

        proporcion = self._suavizado(
            proporcion
        )

        return (
            p.max_radius_mm
            + (
                p.outlet_radius_mm
                - p.max_radius_mm
            )
            * proporcion
        )

    @staticmethod
    def _crear_seccion(
        x_mm: float,
        radio_mm: float,
    ):
        """
        Crea una sección circular perpendicular al eje X.
        """

        if radio_mm <= 0.0:
            raise ValueError(
                "El radio de una sección debe ser "
                "mayor que cero."
            )

        eje = gp_Ax2(
            gp_Pnt(
                float(x_mm),
                0.0,
                0.0,
            ),
            gp_Dir(
                1.0,
                0.0,
                0.0,
            ),
        )

        circulo = gp_Circ(
            eje,
            float(radio_mm),
        )

        arista = BRepBuilderAPI_MakeEdge(
            circulo
        ).Edge()

        constructor_alambre = (
            BRepBuilderAPI_MakeWire()
        )
        constructor_alambre.Add(arista)

        if not constructor_alambre.IsDone():
            raise RuntimeError(
                "OpenCascade no pudo crear una "
                "sección de la góndola."
            )

        return constructor_alambre.Wire()

    def _crear_loft_exterior(self):
        """Construye el volumen exterior cerrado."""

        p = self.parametros

        loft = BRepOffsetAPI_ThruSections(
            True,
            False,
            1.0e-6,
        )

        ultimo_indice = p.num_sections - 1

        for indice in range(
            p.num_sections
        ):
            posicion_relativa = (
                indice / ultimo_indice
            )

            x_mm = (
                posicion_relativa
                * p.length_mm
            )

            radio_mm = self._radio_exterior(
                posicion_relativa
            )

            loft.AddWire(
                self._crear_seccion(
                    x_mm,
                    radio_mm,
                )
            )

        loft.Build()

        if not loft.IsDone():
            raise RuntimeError(
                "OpenCascade no pudo construir "
                "el loft exterior de la góndola."
            )

        resultado = loft.Shape()

        if (
            resultado is None
            or resultado.IsNull()
        ):
            raise RuntimeError(
                "El loft exterior de la góndola "
                "está vacío."
            )

        return resultado

    def _crear_loft_interior(self):
        """
        Construye el volumen que será retirado.

        Se extiende ligeramente más allá de los extremos
        para garantizar que entrada y salida queden abiertas.
        """

        p = self.parametros

        extension_mm = max(
            1.0,
            0.002 * p.length_mm,
        )

        loft = BRepOffsetAPI_ThruSections(
            True,
            False,
            1.0e-6,
        )

        radio_entrada = (
            p.inner_inlet_radius_mm
        )

        loft.AddWire(
            self._crear_seccion(
                -extension_mm,
                radio_entrada,
            )
        )

        ultimo_indice = p.num_sections - 1

        for indice in range(
            p.num_sections
        ):
            posicion_relativa = (
                indice / ultimo_indice
            )

            x_mm = (
                posicion_relativa
                * p.length_mm
            )

            radio_exterior = (
                self._radio_exterior(
                    posicion_relativa
                )
            )

            radio_interior = (
                radio_exterior
                - p.wall_thickness_mm
            )

            loft.AddWire(
                self._crear_seccion(
                    x_mm,
                    radio_interior,
                )
            )

        loft.AddWire(
            self._crear_seccion(
                p.length_mm + extension_mm,
                p.inner_outlet_radius_mm,
            )
        )

        loft.Build()

        if not loft.IsDone():
            raise RuntimeError(
                "OpenCascade no pudo construir "
                "el conducto interior."
            )

        resultado = loft.Shape()

        if (
            resultado is None
            or resultado.IsNull()
        ):
            raise RuntimeError(
                "El conducto interior está vacío."
            )

        return resultado

    def construir(self):
        """
        Construye y devuelve la góndola hueca completa.
        """

        exterior = (
            self._crear_loft_exterior()
        )
        interior = (
            self._crear_loft_interior()
        )

        corte = BRepAlgoAPI_Cut(
            exterior,
            interior,
        )
        corte.Build()

        if not corte.IsDone():
            raise RuntimeError(
                "OpenCascade no pudo vaciar "
                "el interior de la góndola."
            )

        resultado = corte.Shape()

        if (
            resultado is None
            or resultado.IsNull()
        ):
            raise RuntimeError(
                "La góndola generada está vacía."
            )

        analizador = BRepCheck_Analyzer(
            resultado
        )

        if not analizador.IsValid():
            raise RuntimeError(
                "OpenCascade generó una góndola "
                "geométricamente inválida."
            )

        return resultado