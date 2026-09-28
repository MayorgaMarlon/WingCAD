"""Cálculo de propiedades geométricas y másicas con OpenCascade."""

from dataclasses import dataclass

from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps


MODELOS_MASA = {
    "solido",
    "carcasa",
}


@dataclass
class MassProperties:
    """Resultados físicos del modelo CAD."""

    volumen_m3: float
    area_superficial_m2: float
    densidad_kg_m3: float
    masa_kg: float

    cg_x_mm: float
    cg_y_mm: float
    cg_z_mm: float

    inercia_xx_kg_m2: float
    inercia_yy_kg_m2: float
    inercia_zz_kg_m2: float

    inercia_xy_kg_m2: float
    inercia_xz_kg_m2: float
    inercia_yz_kg_m2: float

    modelo_masa: str = "solido"
    espesor_mm: float = 0.0


def validar_modelo_masa(modelo_masa):
    """Normaliza y valida el modelo físico."""

    modelo = str(modelo_masa).strip().lower()

    if modelo not in MODELOS_MASA:
        raise ValueError(
            "El modelo de masa debe ser "
            "'solido' o 'carcasa'."
        )

    return modelo


def calcular_propiedades(
    geometria,
    densidad_kg_m3=2700.0,
    modelo_masa="solido",
    espesor_mm=1.0,
):
    """
    Calcula las propiedades físicas con OpenCascade.

    Modelos disponibles:

    - solido:
      La masa ocupa todo el volumen geométrico.

    - carcasa:
      Aproximación de pared delgada mediante:
      volumen_material = área_superficial * espesor.

    La geometría se expresa en milímetros.
    La densidad se expresa en kg/m³.
    """

    densidad_kg_m3 = float(
        densidad_kg_m3
    )
    modelo_masa = validar_modelo_masa(
        modelo_masa
    )
    espesor_mm = float(
        espesor_mm
    )

    if densidad_kg_m3 <= 0:
        raise ValueError(
            "La densidad debe ser mayor que cero."
        )

    if (
        modelo_masa == "carcasa"
        and espesor_mm <= 0
    ):
        raise ValueError(
            "El espesor de la carcasa debe "
            "ser mayor que cero."
        )

    # =====================================================
    # PROPIEDADES DE SUPERFICIE
    # =====================================================

    propiedades_superficie = GProp_GProps()

    BRepGProp.SurfaceProperties_s(
        geometria,
        propiedades_superficie,
    )

    area_mm2 = propiedades_superficie.Mass()

    if area_mm2 <= 0:
        raise RuntimeError(
            "La geometría no contiene una "
            "superficie válida."
        )

    area_m2 = (
        area_mm2
        / 1_000_000.0
    )

    # =====================================================
    # PROPIEDADES DE VOLUMEN
    # =====================================================

    propiedades_volumen = GProp_GProps()

    BRepGProp.VolumeProperties_s(
        geometria,
        propiedades_volumen,
    )

    volumen_mm3 = propiedades_volumen.Mass()

    if volumen_mm3 <= 0:
        raise RuntimeError(
            "La geometría no contiene un "
            "volumen válido."
        )

    # =====================================================
    # MODELO SÓLIDO
    # =====================================================

    if modelo_masa == "solido":
        volumen_m3 = (
            volumen_mm3
            / 1_000_000_000.0
        )

        masa_kg = (
            densidad_kg_m3
            * volumen_m3
        )

        centro = (
            propiedades_volumen
            .CentreOfMass()
        )

        matriz = (
            propiedades_volumen
            .MatrixOfInertia()
        )

        # La matriz volumétrica está en mm⁵.
        factor_inercia = (
            densidad_kg_m3
            / 1.0e15
        )

        espesor_resultado = 0.0

    # =====================================================
    # MODELO DE CARCASA
    # =====================================================

    else:
        espesor_m = (
            espesor_mm
            / 1000.0
        )

        volumen_m3 = (
            area_m2
            * espesor_m
        )

        masa_kg = (
            densidad_kg_m3
            * volumen_m3
        )

        centro = (
            propiedades_superficie
            .CentreOfMass()
        )

        matriz = (
            propiedades_superficie
            .MatrixOfInertia()
        )

        # La matriz superficial está en mm⁴.
        # Al multiplicarla por densidad y espesor
        # se obtiene la inercia en kg·m².
        factor_inercia = (
            densidad_kg_m3
            * espesor_mm
            / 1.0e15
        )

        espesor_resultado = espesor_mm

    return MassProperties(
        volumen_m3=volumen_m3,
        area_superficial_m2=area_m2,
        densidad_kg_m3=densidad_kg_m3,
        masa_kg=masa_kg,

        cg_x_mm=centro.X(),
        cg_y_mm=centro.Y(),
        cg_z_mm=centro.Z(),

        inercia_xx_kg_m2=(
            matriz.Value(1, 1)
            * factor_inercia
        ),
        inercia_yy_kg_m2=(
            matriz.Value(2, 2)
            * factor_inercia
        ),
        inercia_zz_kg_m2=(
            matriz.Value(3, 3)
            * factor_inercia
        ),

        inercia_xy_kg_m2=(
            matriz.Value(1, 2)
            * factor_inercia
        ),
        inercia_xz_kg_m2=(
            matriz.Value(1, 3)
            * factor_inercia
        ),
        inercia_yz_kg_m2=(
            matriz.Value(2, 3)
            * factor_inercia
        ),

        modelo_masa=modelo_masa,
        espesor_mm=espesor_resultado,
    )