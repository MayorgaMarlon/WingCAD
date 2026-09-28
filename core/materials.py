from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Material:
    identificador: str
    nombre: str
    densidad_kg_m3: float
    descripcion: str = ""

    def validar(self) -> None:
        if not self.identificador.strip():
            raise ValueError(
                "El identificador del material está vacío."
            )

        if not self.nombre.strip():
            raise ValueError(
                "El nombre del material está vacío."
            )

        if self.densidad_kg_m3 <= 0.0:
            raise ValueError(
                "La densidad del material debe ser "
                "mayor que cero."
            )


MATERIALES = {
    "aluminio_2024_t3": Material(
        identificador="aluminio_2024_t3",
        nombre="Aluminio 2024-T3",
        densidad_kg_m3=2780.0,
        descripcion=(
            "Aleación de aluminio utilizada habitualmente "
            "en estructuras aeronáuticas."
        ),
    ),
    "aluminio_6061_t6": Material(
        identificador="aluminio_6061_t6",
        nombre="Aluminio 6061-T6",
        densidad_kg_m3=2700.0,
        descripcion=(
            "Aluminio de buena resistencia mecánica y "
            "facilidad de fabricación."
        ),
    ),
    "aluminio_7075_t6": Material(
        identificador="aluminio_7075_t6",
        nombre="Aluminio 7075-T6",
        densidad_kg_m3=2810.0,
        descripcion=(
            "Aleación de aluminio de alta resistencia."
        ),
    ),
    "acero_estructural": Material(
        identificador="acero_estructural",
        nombre="Acero estructural",
        densidad_kg_m3=7850.0,
        descripcion=(
            "Valor representativo para componentes "
            "estructurales de acero."
        ),
    ),
    "titanio_ti6al4v": Material(
        identificador="titanio_ti6al4v",
        nombre="Titanio Ti-6Al-4V",
        densidad_kg_m3=4430.0,
        descripcion=(
            "Aleación de titanio de uso aeroespacial."
        ),
    ),
    "fibra_carbono": Material(
        identificador="fibra_carbono",
        nombre="Compuesto de fibra de carbono",
        densidad_kg_m3=1600.0,
        descripcion=(
            "Densidad representativa de un laminado CFRP."
        ),
    ),
    "fibra_vidrio": Material(
        identificador="fibra_vidrio",
        nombre="Compuesto de fibra de vidrio",
        densidad_kg_m3=1900.0,
        descripcion=(
            "Densidad representativa de un laminado GFRP."
        ),
    ),
}


def listar_materiales() -> tuple[Material, ...]:
    """
    Devuelve todos los materiales ordenados por nombre.
    """

    return tuple(
        sorted(
            MATERIALES.values(),
            key=lambda material: material.nombre,
        )
    )


def obtener_material(
    identificador: str,
) -> Material:
    """
    Obtiene un material utilizando su identificador.
    """

    identificador = str(identificador).strip()

    try:
        return MATERIALES[identificador]
    except KeyError as error:
        raise ValueError(
            f"Material desconocido: {identificador}"
        ) from error


def buscar_material_por_densidad(
    densidad_kg_m3: float,
    tolerancia_kg_m3: float = 1.0,
) -> Optional[Material]:
    """
    Busca un material cuya densidad coincida aproximadamente
    con la densidad indicada.
    """

    densidad_kg_m3 = float(densidad_kg_m3)
    tolerancia_kg_m3 = abs(
        float(tolerancia_kg_m3)
    )

    for material in MATERIALES.values():
        diferencia = abs(
            material.densidad_kg_m3
            - densidad_kg_m3
        )

        if diferencia <= tolerancia_kg_m3:
            return material

    return None