"""Parámetros y validación del ala paramétrica."""

from dataclasses import dataclass


@dataclass
class WingParameters:
    """Conjunto de parámetros necesarios para construir un ala."""

    perfil_raiz: str = "2412"
    perfil_punta: str = "2412"

    cuerda_raiz_mm: float = 1000.0
    cuerda_punta_mm: float = 500.0

    semi_span_mm: float = 4000.0

    flecha_grados: float = 15.0
    diedro_grados: float = 3.0
    torsion_punta_grados: float = -3.0

    numero_puntos: int = 60
    numero_secciones: int = 10

    def validar(self):
        """Comprueba que todos los parámetros sean utilizables."""

        self._validar_naca(self.perfil_raiz, "perfil raíz")
        self._validar_naca(self.perfil_punta, "perfil punta")

        if self.cuerda_raiz_mm <= 0:
            raise ValueError("La cuerda raíz debe ser mayor que cero.")

        if self.cuerda_punta_mm <= 0:
            raise ValueError("La cuerda punta debe ser mayor que cero.")

        if self.semi_span_mm <= 0:
            raise ValueError("La semienvergadura debe ser mayor que cero.")

        if not -45.0 <= self.flecha_grados <= 75.0:
            raise ValueError(
                "La flecha debe estar entre -45° y 75°."
            )

        if not -20.0 <= self.diedro_grados <= 45.0:
            raise ValueError(
                "El diedro debe estar entre -20° y 45°."
            )

        if not -20.0 <= self.torsion_punta_grados <= 20.0:
            raise ValueError(
                "La torsión debe estar entre -20° y 20°."
            )

        if not 20 <= self.numero_puntos <= 300:
            raise ValueError(
                "El número de puntos debe estar entre 20 y 300."
            )
        if not 2 <= self.numero_secciones <= 50:
            raise ValueError(
                "El número de secciones debe estar entre 2 y 50."
            )

    @staticmethod
    def _validar_naca(codigo, nombre):
        """Valida un código NACA de cuatro dígitos."""

        if len(codigo) != 4 or not codigo.isdigit():
            raise ValueError(
                f"El {nombre} debe ser un código NACA de cuatro dígitos."
            )

    @property
    def envergadura_total_mm(self):
        """Envergadura total suponiendo un ala simétrica."""

        return 2.0 * self.semi_span_mm

    @property
    def relacion_estrechamiento(self):
        """Relación entre cuerda de punta y cuerda raíz."""

        return self.cuerda_punta_mm / self.cuerda_raiz_mm

    @property
    def superficie_aproximada_mm2(self):
        """Área en planta aproximada del ala completa."""

        area_semiala = (
            0.5
            * (self.cuerda_raiz_mm + self.cuerda_punta_mm)
            * self.semi_span_mm
        )

        return 2.0 * area_semiala

    @property
    def alargamiento_aproximado(self):
        """Relación de aspecto aproximada del ala completa."""

        return (
            self.envergadura_total_mm**2
            / self.superficie_aproximada_mm2
        )