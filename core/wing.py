"""Motor geométrico OpenCascade para superficies aerodinámicas."""

import math

from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse
from OCP.BRepBuilderAPI import (
    BRepBuilderAPI_MakeEdge,
    BRepBuilderAPI_MakeWire,
    BRepBuilderAPI_Transform,
)
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepOffsetAPI import BRepOffsetAPI_ThruSections
from OCP.GeomAPI import GeomAPI_PointsToBSpline
from OCP.TColgp import TColgp_Array1OfPnt
from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt, gp_Trsf

from core.naca import puntos_naca4
from core.parameters import WingParameters


class WingBuilder:
    """Construye una superficie simétrica o una semiala mediante lofts."""

    MODOS_SUPERFICIE = {
        "simetrica",
        "semiala_positiva",
        "semiala_negativa",
    }

    def __init__(
        self,
        parametros: WingParameters,
        modo_superficie: str = "simetrica",
    ):
        self.parametros = parametros
        self.parametros.validar()

        modo_superficie = str(modo_superficie).strip().lower()

        if modo_superficie not in self.MODOS_SUPERFICIE:
            raise ValueError("Modo de superficie no válido.")

        self.modo_superficie = modo_superficie

    @staticmethod
    def _interpolar_puntos(puntos_raiz, puntos_punta, factor):
        resultado = []

        for punto_raiz, punto_punta in zip(
            puntos_raiz,
            puntos_punta,
        ):
            x = (
                (1.0 - factor) * punto_raiz.X()
                + factor * punto_punta.X()
            )

            z = (
                (1.0 - factor) * punto_raiz.Z()
                + factor * punto_punta.Z()
            )

            resultado.append(gp_Pnt(x, 0.0, z))

        return resultado

    def _obtener_perfil_interpolado(self, cuerda, factor):
        p = self.parametros

        superior_raiz, inferior_raiz = puntos_naca4(
            codigo=p.perfil_raiz,
            cuerda=cuerda,
            numero_puntos=p.numero_puntos,
        )

        superior_punta, inferior_punta = puntos_naca4(
            codigo=p.perfil_punta,
            cuerda=cuerda,
            numero_puntos=p.numero_puntos,
        )

        superiores = self._interpolar_puntos(
            superior_raiz,
            superior_punta,
            factor,
        )

        inferiores = self._interpolar_puntos(
            inferior_raiz,
            inferior_punta,
            factor,
        )

        return superiores, inferiores

    @staticmethod
    def _transformar_punto(
        punto,
        cuerda,
        posicion_y,
        desplazamiento_x,
        desplazamiento_z,
        torsion_grados,
    ):
        """Aplica torsión alrededor del cuarto de cuerda."""

        angulo = math.radians(torsion_grados)
        eje_torsion = 0.25 * cuerda

        x_centrado = punto.X() - eje_torsion
        z_local = punto.Z()

        x_rotado = (
            x_centrado * math.cos(angulo)
            + z_local * math.sin(angulo)
        )

        z_rotado = (
            -x_centrado * math.sin(angulo)
            + z_local * math.cos(angulo)
        )

        return gp_Pnt(
            x_rotado + eje_torsion + desplazamiento_x,
            posicion_y,
            z_rotado + desplazamiento_z,
        )

    @staticmethod
    def _crear_curva_bspline(puntos):
        arreglo = TColgp_Array1OfPnt(1, len(puntos))

        for indice, punto in enumerate(puntos, start=1):
            arreglo.SetValue(indice, punto)

        constructor = GeomAPI_PointsToBSpline(arreglo)

        if not constructor.IsDone():
            raise RuntimeError("No se pudo crear la curva B-Spline.")

        return constructor.Curve()

    def _crear_seccion(
        self,
        cuerda,
        posicion_y,
        desplazamiento_x,
        desplazamiento_z,
        torsion_grados,
        factor_perfil,
    ):
        superiores, inferiores = self._obtener_perfil_interpolado(
            cuerda,
            factor_perfil,
        )

        superiores_transformados = [
            self._transformar_punto(
                punto,
                cuerda,
                posicion_y,
                desplazamiento_x,
                desplazamiento_z,
                torsion_grados,
            )
            for punto in superiores
        ]

        inferiores_transformados = [
            self._transformar_punto(
                punto,
                cuerda,
                posicion_y,
                desplazamiento_x,
                desplazamiento_z,
                torsion_grados,
            )
            for punto in inferiores
        ]

        curva_superior = self._crear_curva_bspline(
            list(reversed(superiores_transformados))
        )

        curva_inferior = self._crear_curva_bspline(
            inferiores_transformados
        )

        constructor_wire = BRepBuilderAPI_MakeWire()

        constructor_wire.Add(
            BRepBuilderAPI_MakeEdge(curva_superior).Edge()
        )

        constructor_wire.Add(
            BRepBuilderAPI_MakeEdge(curva_inferior).Edge()
        )

        if not constructor_wire.IsDone():
            raise RuntimeError(
                f"No se pudo crear la sección en Y={posicion_y:.2f} mm."
            )

        return constructor_wire.Wire()

    def _construir_semiala_positiva(self):
        """Genera la semiala situada en Y positivo."""

        p = self.parametros

        tangente_flecha = math.tan(
            math.radians(p.flecha_grados)
        )

        tangente_diedro = math.tan(
            math.radians(p.diedro_grados)
        )

        loft = BRepOffsetAPI_ThruSections(
            True,
            False,
            1.0e-6,
        )

        loft.CheckCompatibility(True)

        for indice in range(p.numero_secciones):
            factor = indice / (p.numero_secciones - 1)

            posicion_y = factor * p.semi_span_mm

            cuerda = (
                (1.0 - factor) * p.cuerda_raiz_mm
                + factor * p.cuerda_punta_mm
            )

            desplazamiento_x = posicion_y * tangente_flecha
            desplazamiento_z = posicion_y * tangente_diedro

            torsion = factor * p.torsion_punta_grados

            seccion = self._crear_seccion(
                cuerda=cuerda,
                posicion_y=posicion_y,
                desplazamiento_x=desplazamiento_x,
                desplazamiento_z=desplazamiento_z,
                torsion_grados=torsion,
                factor_perfil=factor,
            )

            loft.AddWire(seccion)

        loft.Build()

        if not loft.IsDone():
            raise RuntimeError(
                "OpenCascade no pudo construir el loft."
            )

        semiala = loft.Shape()

        if semiala.IsNull():
            raise RuntimeError(
                "OpenCascade generó una semiala vacía."
            )

        if not BRepCheck_Analyzer(semiala).IsValid():
            raise RuntimeError(
                "La semiala no es geométricamente válida."
            )

        return semiala

    @staticmethod
    def _reflejar_en_plano_y(forma):
        plano_simetria = gp_Ax2(
            gp_Pnt(0.0, 0.0, 0.0),
            gp_Dir(0.0, 1.0, 0.0),
        )

        transformacion = gp_Trsf()
        transformacion.SetMirror(plano_simetria)

        return BRepBuilderAPI_Transform(
            forma,
            transformacion,
            True,
        ).Shape()

    def construir(self):
        """Construye la superficie de acuerdo con el modo configurado."""

        semiala_positiva = self._construir_semiala_positiva()

        if self.modo_superficie == "semiala_positiva":
            return semiala_positiva

        semiala_negativa = self._reflejar_en_plano_y(
            semiala_positiva
        )

        if semiala_negativa.IsNull():
            raise RuntimeError(
                "No se pudo reflejar la semiala."
            )

        if self.modo_superficie == "semiala_negativa":
            return semiala_negativa

        fusion = BRepAlgoAPI_Fuse(
            semiala_positiva,
            semiala_negativa,
        )

        fusion.Build()

        if not fusion.IsDone():
            raise RuntimeError(
                "No se pudieron unir las dos semialas."
            )

        ala_completa = fusion.Shape()

        if ala_completa.IsNull():
            raise RuntimeError(
                "La unión generó una geometría vacía."
            )

        if not BRepCheck_Analyzer(ala_completa).IsValid():
            raise RuntimeError(
                "El ala completa no es válida."
            )

        return ala_completa