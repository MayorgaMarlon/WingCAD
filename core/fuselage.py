"""Construcción paramétrica del fuselaje con OpenCascade."""

import math

from OCP.BRepBuilderAPI import (
    BRepBuilderAPI_MakeEdge,
    BRepBuilderAPI_MakeVertex,
    BRepBuilderAPI_MakeWire,
)
from OCP.BRepOffsetAPI import (
    BRepOffsetAPI_ThruSections,
)
from OCP.Geom import Geom_Ellipse
from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt

from core.fuselage_parameters import (
    FuselageParameters,
)


class FuselageBuilder:
    """
    Generador paramétrico de fuselajes mediante lofts.

    Sistema de coordenadas:

    - X: dirección longitudinal.
    - Y: dirección transversal.
    - Z: dirección vertical.
    """

    def __init__(
        self,
        parametros: FuselageParameters,
    ):
        if not isinstance(
            parametros,
            FuselageParameters,
        ):
            raise TypeError(
                "parametros debe ser FuselageParameters."
            )

        parametros.validar()
        self.parametros = parametros

    @staticmethod
    def _limitar(
        valor: float,
    ) -> float:
        """Limita un valor entre 0 y 1."""

        return max(
            0.0,
            min(
                1.0,
                valor,
            ),
        )

    @staticmethod
    def _distribuir_seccion(
        indice: int,
        ultimo_indice: int,
    ) -> float:
        """
        Distribuye las estaciones longitudinales.

        La distribución cosenoidal concentra más secciones
        cerca de la nariz y de la cola.
        """

        angulo = (
            math.pi
            * indice
            / ultimo_indice
        )

        return (
            0.5
            * (
                1.0
                - math.cos(angulo)
            )
        )

    def _escala_seccion(
        self,
        posicion_relativa: float,
    ) -> float:
        """
        Calcula la escala transversal de una sección.
        """

        p = self.parametros

        posicion_relativa = self._limitar(
            posicion_relativa
        )

        if posicion_relativa <= 0.0:
            return 0.0

        if posicion_relativa >= 1.0:
            return p.tail_end_ratio

        # =====================================================
        # NARIZ
        # =====================================================

        if posicion_relativa < p.nose_ratio:
            posicion_local = (
                posicion_relativa
                / p.nose_ratio
            )

            posicion_local = self._limitar(
                posicion_local
            )

            escala_elipsoidal = math.sqrt(
                max(
                    0.0,
                    posicion_local
                    * (
                        2.0
                        - posicion_local
                    ),
                )
            )

            return (
                escala_elipsoidal
                ** p.nose_roundness
            )

        # =====================================================
        # COLA
        # =====================================================

        inicio_cola = (
            1.0
            - p.tail_ratio
        )

        if posicion_relativa > inicio_cola:
            posicion_local = (
                posicion_relativa
                - inicio_cola
            ) / p.tail_ratio

            posicion_local = self._limitar(
                posicion_local
            )

            escala_elipsoidal = math.sqrt(
                max(
                    0.0,
                    1.0
                    - posicion_local
                    * posicion_local,
                )
            )

            escala_forma = (
                escala_elipsoidal
                ** p.tail_roundness
            )

            return (
                p.tail_end_ratio
                + (
                    1.0
                    - p.tail_end_ratio
                )
                * escala_forma
            )

        return 1.0

    def _crear_seccion(
        self,
        x_mm: float,
        escala: float,
    ):
        """
        Crea una sección elíptica perpendicular al eje X.
        """

        p = self.parametros

        radio_y = (
            0.5
            * p.max_width_mm
            * escala
        )

        radio_z = (
            0.5
            * p.max_height_mm
            * escala
        )

        if radio_y <= 0.0:
            raise ValueError(
                "El radio transversal debe ser mayor que cero."
            )

        if radio_z <= 0.0:
            raise ValueError(
                "El radio vertical debe ser mayor que cero."
            )

        # Geom_Ellipse requiere que el radio mayor sea
        # el primer radio proporcionado.
        if radio_y >= radio_z:
            eje = gp_Ax2(
                gp_Pnt(
                    x_mm,
                    0.0,
                    0.0,
                ),
                gp_Dir(
                    1.0,
                    0.0,
                    0.0,
                ),
                gp_Dir(
                    0.0,
                    1.0,
                    0.0,
                ),
            )

            radio_mayor = radio_y
            radio_menor = radio_z

        else:
            eje = gp_Ax2(
                gp_Pnt(
                    x_mm,
                    0.0,
                    0.0,
                ),
                gp_Dir(
                    1.0,
                    0.0,
                    0.0,
                ),
                gp_Dir(
                    0.0,
                    0.0,
                    1.0,
                ),
            )

            radio_mayor = radio_z
            radio_menor = radio_y

        elipse = Geom_Ellipse(
            eje,
            radio_mayor,
            radio_menor,
        )

        constructor_arista = (
            BRepBuilderAPI_MakeEdge(
                elipse
            )
        )

        if not constructor_arista.IsDone():
            raise RuntimeError(
                "No se pudo crear una sección "
                "elíptica del fuselaje."
            )

        arista = constructor_arista.Edge()

        constructor_alambre = (
            BRepBuilderAPI_MakeWire(
                arista
            )
        )

        if not constructor_alambre.IsDone():
            raise RuntimeError(
                "No se pudo cerrar una sección "
                "del fuselaje."
            )

        return constructor_alambre.Wire()

    @staticmethod
    def _crear_vertice(
        x_mm: float,
    ):
        """Crea un vértice en un extremo del fuselaje."""

        constructor = (
            BRepBuilderAPI_MakeVertex(
                gp_Pnt(
                    x_mm,
                    0.0,
                    0.0,
                )
            )
        )

        if not constructor.IsDone():
            raise RuntimeError(
                "No se pudo crear un extremo "
                "del fuselaje."
            )

        return constructor.Vertex()

    def construir(self):
        """
        Construye el fuselaje como un sólido cerrado.

        La primera y la última estación son vértices.
        Las estaciones interiores son elipses cerradas.
        """

        p = self.parametros

        loft = BRepOffsetAPI_ThruSections(
            True,
            False,
            1.0e-6,
        )

        loft.CheckCompatibility(True)

        # El suavizado se controla mediante la distribución
        # geométrica de las secciones.
        loft.SetSmoothing(False)

        ultimo_indice = (
            p.num_sections
            - 1
        )

        for indice in range(
            p.num_sections
        ):
            fraccion = (
                self._distribuir_seccion(
                    indice,
                    ultimo_indice,
                )
            )

            x_mm = (
                p.length_mm
                * fraccion
            )

            # Extremo delantero.
            if indice == 0:
                loft.AddVertex(
                    self._crear_vertice(
                        x_mm
                    )
                )
                continue

            # Cola puntual o truncada.
            if indice == ultimo_indice:
                if p.tail_end_ratio <= 1.0e-9:
                    loft.AddVertex(
                        self._crear_vertice(
                            x_mm
                        )
                    )
                else:
                    loft.AddWire(
                        self._crear_seccion(
                            x_mm,
                            p.tail_end_ratio,
                        )
                    )

                continue

            escala = self._escala_seccion(
                fraccion
            )

            seccion = self._crear_seccion(
                x_mm,
                escala,
            )

            loft.AddWire(
                seccion
            )

        loft.Build()

        if not loft.IsDone():
            raise RuntimeError(
                "OpenCascade no pudo construir "
                "el loft del fuselaje."
            )

        resultado = loft.Shape()

        if (
            resultado is None
            or resultado.IsNull()
        ):
            raise RuntimeError(
                "El fuselaje generado está vacío."
            )

        return resultado