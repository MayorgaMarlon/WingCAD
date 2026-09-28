"""Componente paramétrico para superficies aerodinámicas."""

from dataclasses import asdict, replace

from app.cad_object import CADObject
from core.parameters import WingParameters
from core.properties import (
    calcular_propiedades,
    validar_modelo_masa,
)
from core.wing import WingBuilder
from geometry.placement import Placement


class WingComponent(CADObject):
    """Superficie aerodinámica paramétrica."""

    tipo = "Ala"

    MODOS_SUPERFICIE = {
        "simetrica",
        "semiala_positiva",
        "semiala_negativa",
    }

    def __init__(
        self,
        nombre: str = "Ala",
        parametros: WingParameters | None = None,
        densidad: float = 2700.0,
        placement: Placement | None = None,
        modo_superficie: str = "simetrica",
        modelo_masa: str = "solido",
        espesor_mm: float = 2.0,
    ):
        super().__init__(
            nombre=nombre,
            placement=placement,
        )

        self.parametros = (
            parametros
            or WingParameters()
        )
        self.parametros.validar()

        densidad = float(
            densidad
        )

        if densidad <= 0:
            raise ValueError(
                "La densidad debe ser mayor que cero."
            )

        self.densidad = densidad

        self.modelo_masa = validar_modelo_masa(
            modelo_masa
        )

        self.espesor_mm = float(
            espesor_mm
        )

        if self.espesor_mm <= 0:
            raise ValueError(
                "El espesor debe ser mayor que cero."
            )

        self.modo_superficie = (
            self._validar_modo_superficie(
                modo_superficie
            )
        )

        self.propiedades = None

    @classmethod
    def _validar_modo_superficie(
        cls,
        modo: str,
    ) -> str:
        modo = str(
            modo
        ).strip().lower()

        if modo not in cls.MODOS_SUPERFICIE:
            raise ValueError(
                "Modo de superficie no válido. "
                "Use: simetrica, semiala_positiva "
                "o semiala_negativa."
            )

        return modo

    @property
    def densidad_kg_m3(self) -> float:
        return self.densidad

    @densidad_kg_m3.setter
    def densidad_kg_m3(
        self,
        valor: float,
    ):
        valor = float(
            valor
        )

        if valor <= 0:
            raise ValueError(
                "La densidad debe ser mayor que cero."
            )

        self.densidad = valor

    def construir_geometria(self):
        """Construye la geometría local."""

        self.parametros.validar()

        constructor = WingBuilder(
            self.parametros,
            modo_superficie=(
                self.modo_superficie
            ),
        )

        geometria = constructor.construir()

        if (
            geometria is None
            or geometria.IsNull()
        ):
            raise RuntimeError(
                "No se pudo construir la geometría "
                f"de {self.nombre}."
            )

        return geometria

    def actualizar_resultados(self):
        """Calcula propiedades de masa."""

        if (
            self.shape is None
            or self.shape.IsNull()
        ):
            self.propiedades = None
            return

        self.propiedades = calcular_propiedades(
            self.shape,
            self.densidad,
            modelo_masa=self.modelo_masa,
            espesor_mm=self.espesor_mm,
        )

    def establecer_densidad(
        self,
        densidad: float,
    ):
        self.densidad_kg_m3 = densidad

        if (
            self.shape is not None
            and not self.shape.IsNull()
        ):
            self.actualizar_resultados()

    def establecer_modelo_masa(
        self,
        modelo_masa: str,
        espesor_mm: float | None = None,
    ):
        """Cambia entre sólido y carcasa."""

        self.modelo_masa = validar_modelo_masa(
            modelo_masa
        )

        if espesor_mm is not None:
            espesor_mm = float(
                espesor_mm
            )

            if espesor_mm <= 0:
                raise ValueError(
                    "El espesor debe ser "
                    "mayor que cero."
                )

            self.espesor_mm = espesor_mm

        if (
            self.shape is not None
            and not self.shape.IsNull()
        ):
            self.actualizar_resultados()

    def establecer_parametros(
        self,
        parametros: WingParameters,
    ):
        if not isinstance(
            parametros,
            WingParameters,
        ):
            raise TypeError(
                "parametros debe ser una instancia "
                "de WingParameters."
            )

        parametros.validar()

        self.parametros = parametros
        self.marcar_modificado()

    def actualizar_parametros(
        self,
        **cambios,
    ):
        nuevos_parametros = replace(
            self.parametros,
            **cambios,
        )

        nuevos_parametros.validar()

        self.parametros = nuevos_parametros
        self.marcar_modificado()

    def establecer_modo_superficie(
        self,
        modo_superficie: str,
    ):
        """Cambia entre ala completa y semialas."""

        modo_superficie = (
            self._validar_modo_superficie(
                modo_superficie
            )
        )

        if (
            modo_superficie
            != self.modo_superficie
        ):
            self.modo_superficie = (
                modo_superficie
            )
            self.marcar_modificado()

    def obtener_parametros(self) -> dict:
        return asdict(
            self.parametros
        )

    def obtener_resumen(self) -> dict:
        resumen = super().obtener_resumen()

        if self.propiedades is None:
            propiedades = {}
        else:
            propiedades = asdict(
                self.propiedades
            )

        resumen.update(
            {
                "densidad_kg_m3": (
                    self.densidad_kg_m3
                ),
                "modelo_masa": (
                    self.modelo_masa
                ),
                "espesor_mm": (
                    self.espesor_mm
                ),
                "modo_superficie": (
                    self.modo_superficie
                ),
                "parametros": (
                    self.obtener_parametros()
                ),
                "propiedades": propiedades,
            }
        )

        return resumen