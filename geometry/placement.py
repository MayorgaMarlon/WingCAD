"""Posición y orientación de objetos dentro del ensamblaje."""

import math
from dataclasses import asdict, dataclass

from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.gp import (
    gp_Ax1,
    gp_Dir,
    gp_Pnt,
    gp_Trsf,
    gp_Vec,
)


@dataclass
class Placement:
    """
    Transformación de un objeto CAD.

    Las posiciones están expresadas en milímetros.
    Los ángulos están expresados en grados.
    """

    x_mm: float = 0.0
    y_mm: float = 0.0
    z_mm: float = 0.0

    roll_deg: float = 0.0
    pitch_deg: float = 0.0
    yaw_deg: float = 0.0

    def validar(self):
        """Comprueba que todos los valores sean numéricos."""

        valores = asdict(self)

        for nombre, valor in valores.items():
            if not isinstance(valor, (int, float)):
                raise TypeError(
                    f"'{nombre}' debe ser numérico."
                )

            if not math.isfinite(valor):
                raise ValueError(
                    f"'{nombre}' debe ser un valor finito."
                )

    def crear_transformacion(self):
        """
        Crea una transformación OpenCascade.

        Convención de rotaciones:
        roll  → eje X
        pitch → eje Y
        yaw   → eje Z
        """

        self.validar()

        origen = gp_Pnt(0.0, 0.0, 0.0)

        rotacion_x = gp_Trsf()
        rotacion_x.SetRotation(
            gp_Ax1(
                origen,
                gp_Dir(1.0, 0.0, 0.0),
            ),
            math.radians(self.roll_deg),
        )

        rotacion_y = gp_Trsf()
        rotacion_y.SetRotation(
            gp_Ax1(
                origen,
                gp_Dir(0.0, 1.0, 0.0),
            ),
            math.radians(self.pitch_deg),
        )

        rotacion_z = gp_Trsf()
        rotacion_z.SetRotation(
            gp_Ax1(
                origen,
                gp_Dir(0.0, 0.0, 1.0),
            ),
            math.radians(self.yaw_deg),
        )

        transformacion = gp_Trsf()

        transformacion.SetTranslation(
            gp_Vec(
                self.x_mm,
                self.y_mm,
                self.z_mm,
            )
        )

        transformacion.Multiply(rotacion_z)
        transformacion.Multiply(rotacion_y)
        transformacion.Multiply(rotacion_x)

        return transformacion

    def aplicar(self, geometria):
        """Aplica la transformación a una geometría."""

        if geometria is None:
            raise ValueError(
                "No se recibió una geometría."
            )

        if geometria.IsNull():
            raise ValueError(
                "No se puede transformar una geometría vacía."
            )

        transformacion = self.crear_transformacion()

        constructor = BRepBuilderAPI_Transform(
            geometria,
            transformacion,
            True,
        )

        constructor.Build()

        if not constructor.IsDone():
            raise RuntimeError(
                "OpenCascade no pudo transformar el objeto."
            )

        resultado = constructor.Shape()

        if resultado.IsNull():
            raise RuntimeError(
                "La transformación produjo una geometría vacía."
            )

        return resultado

    def es_identidad(self):
        """Indica si no existe traslación ni rotación."""

        tolerancia = 1.0e-12

        return all(
            abs(valor) <= tolerancia
            for valor in (
                self.x_mm,
                self.y_mm,
                self.z_mm,
                self.roll_deg,
                self.pitch_deg,
                self.yaw_deg,
            )
        )

    def como_diccionario(self):
        """Devuelve la transformación como diccionario."""

        return asdict(self)

    @classmethod
    def desde_diccionario(cls, datos):
        """Reconstruye un placement guardado en un proyecto WingCAD."""

        if not isinstance(datos, dict):
            raise TypeError(
                "El placement guardado debe ser un diccionario."
            )

        campos = set(cls.__dataclass_fields__)
        desconocidos = set(datos) - campos

        if desconocidos:
            nombres = ", ".join(sorted(desconocidos))
            raise ValueError(
                f"El placement contiene campos desconocidos: {nombres}."
            )

        valores = {
            campo: datos.get(campo, 0.0)
            for campo in cls.__dataclass_fields__
        }

        placement = cls(**valores)
        placement.validar()

        return placement