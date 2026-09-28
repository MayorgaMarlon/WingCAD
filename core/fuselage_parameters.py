"""Parámetros geométricos del fuselaje."""

from dataclasses import dataclass


@dataclass(frozen=True)
class FuselageParameters:
    """
    Parámetros geométricos de un fuselaje elíptico.

    Todas las dimensiones están expresadas en milímetros.
    """

    length_mm: float = 8000.0
    max_width_mm: float = 1200.0
    max_height_mm: float = 1400.0

    nose_ratio: float = 0.20
    tail_ratio: float = 0.30

    # 1.0 representa una distribución elipsoidal.
    # Valores mayores producen una forma más afinada.
    # Valores menores producen una forma más voluminosa.
    nose_roundness: float = 1.00
    tail_roundness: float = 1.45
    tail_end_ratio: float = 0.00

    num_sections: int = 18

    def validar(self):
        """Valida todos los parámetros geométricos."""

        if self.length_mm <= 0:
            raise ValueError(
                "La longitud del fuselaje debe ser mayor que cero."
            )

        if self.max_width_mm <= 0:
            raise ValueError(
                "El ancho del fuselaje debe ser mayor que cero."
            )

        if self.max_height_mm <= 0:
            raise ValueError(
                "La altura del fuselaje debe ser mayor que cero."
            )

        if not 0.05 <= self.nose_ratio <= 0.45:
            raise ValueError(
                "La proporción de nariz debe estar "
                "entre 0.05 y 0.45."
            )

        if not 0.05 <= self.tail_ratio <= 0.60:
            raise ValueError(
                "La proporción de cola debe estar "
                "entre 0.05 y 0.60."
            )

        if self.nose_ratio + self.tail_ratio >= 0.90:
            raise ValueError(
                "La nariz y la cola ocupan demasiado fuselaje."
            )

        if not 0.40 <= self.nose_roundness <= 2.50:
            raise ValueError(
                "La redondez de nariz debe estar "
                "entre 0.40 y 2.50."
            )

        if not 0.40 <= self.tail_roundness <= 2.50:
            raise ValueError(
                "La redondez de cola debe estar "
                "entre 0.40 y 2.50."
            )
        if not 0.0 <= self.tail_end_ratio <= 0.35:
            raise ValueError(
                "La sección final de cola debe estar "
                "entre 0.0 y 0.35."
            )
        if self.num_sections < 6:
            raise ValueError(
                "El fuselaje necesita al menos 6 secciones."
            )

        if self.num_sections > 100:
            raise ValueError(
                "El número máximo de secciones es 100."
            )