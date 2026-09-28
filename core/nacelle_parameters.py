"""Parámetros geométricos de una góndola de motor."""

from dataclasses import dataclass


@dataclass(frozen=True)
class NacelleParameters:
    """
    Parámetros geométricos de una góndola aeronáutica.

    Todas las dimensiones están expresadas en milímetros.
    """

    length_mm: float = 1800.0

    inlet_diameter_mm: float = 900.0
    max_diameter_mm: float = 1050.0
    outlet_diameter_mm: float = 760.0

    wall_thickness_mm: float = 20.0

    max_diameter_position_ratio: float = 0.35

    num_sections: int = 18

    def validar(self) -> None:
        """Valida todos los parámetros de la góndola."""

        if self.length_mm <= 0.0:
            raise ValueError(
                "La longitud de la góndola debe ser "
                "mayor que cero."
            )

        if self.inlet_diameter_mm <= 0.0:
            raise ValueError(
                "El diámetro de entrada debe ser "
                "mayor que cero."
            )

        if self.max_diameter_mm <= 0.0:
            raise ValueError(
                "El diámetro máximo debe ser "
                "mayor que cero."
            )

        if self.outlet_diameter_mm <= 0.0:
            raise ValueError(
                "El diámetro de salida debe ser "
                "mayor que cero."
            )

        if self.max_diameter_mm < self.inlet_diameter_mm:
            raise ValueError(
                "El diámetro máximo no puede ser menor "
                "que el diámetro de entrada."
            )

        if self.max_diameter_mm < self.outlet_diameter_mm:
            raise ValueError(
                "El diámetro máximo no puede ser menor "
                "que el diámetro de salida."
            )

        if self.wall_thickness_mm <= 0.0:
            raise ValueError(
                "El espesor de pared debe ser "
                "mayor que cero."
            )

        diametro_minimo = min(
            self.inlet_diameter_mm,
            self.outlet_diameter_mm,
        )

        if self.wall_thickness_mm >= 0.45 * diametro_minimo:
            raise ValueError(
                "El espesor de pared es demasiado grande "
                "para los diámetros de la góndola."
            )

        if not (
            0.15
            <= self.max_diameter_position_ratio
            <= 0.75
        ):
            raise ValueError(
                "La posición del diámetro máximo debe "
                "estar entre 0.15 y 0.75."
            )

        if self.num_sections < 6:
            raise ValueError(
                "La góndola necesita al menos "
                "6 secciones."
            )

        if self.num_sections > 80:
            raise ValueError(
                "El número máximo de secciones es 80."
            )

    @property
    def inlet_radius_mm(self) -> float:
        return 0.5 * self.inlet_diameter_mm

    @property
    def max_radius_mm(self) -> float:
        return 0.5 * self.max_diameter_mm

    @property
    def outlet_radius_mm(self) -> float:
        return 0.5 * self.outlet_diameter_mm

    @property
    def inner_inlet_radius_mm(self) -> float:
        return (
            self.inlet_radius_mm
            - self.wall_thickness_mm
        )

    @property
    def inner_max_radius_mm(self) -> float:
        return (
            self.max_radius_mm
            - self.wall_thickness_mm
        )

    @property
    def inner_outlet_radius_mm(self) -> float:
        return (
            self.outlet_radius_mm
            - self.wall_thickness_mm
        )

    def como_diccionario(self) -> dict:
        """Devuelve los parámetros en un diccionario."""

        return {
            "length_mm": self.length_mm,
            "inlet_diameter_mm": (
                self.inlet_diameter_mm
            ),
            "max_diameter_mm": (
                self.max_diameter_mm
            ),
            "outlet_diameter_mm": (
                self.outlet_diameter_mm
            ),
            "wall_thickness_mm": (
                self.wall_thickness_mm
            ),
            "max_diameter_position_ratio": (
                self.max_diameter_position_ratio
            ),
            "num_sections": self.num_sections,
        }