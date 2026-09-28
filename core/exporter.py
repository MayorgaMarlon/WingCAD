"""Exportación de geometrías CAD."""

from pathlib import Path

from OCP.BRep import BRep_Builder
from OCP.IFSelect import IFSelect_RetDone
from OCP.STEPControl import (
    STEPControl_AsIs,
    STEPControl_Writer,
)
from OCP.TopoDS import TopoDS_Compound


def _preparar_ruta(archivo):
    """Prepara la carpeta donde se guardará el STEP."""

    ruta = Path(archivo)
    ruta.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    return ruta


def exportar_step(geometria, archivo):
    """Exporta una geometría OpenCascade a STEP."""

    if (
        geometria is None
        or geometria.IsNull()
    ):
        raise ValueError(
            "La geometría que se intenta exportar "
            "está vacía."
        )

    ruta = _preparar_ruta(archivo)
    escritor = STEPControl_Writer()

    estado = escritor.Transfer(
        geometria,
        STEPControl_AsIs,
    )

    if estado != IFSelect_RetDone:
        raise RuntimeError(
            "No se pudo transferir la geometría "
            "al formato STEP."
        )

    estado = escritor.Write(
        str(ruta)
    )

    if estado != IFSelect_RetDone:
        raise RuntimeError(
            "No se pudo escribir el archivo STEP."
        )

    return ruta.resolve()


def crear_compuesto(geometrias):
    """
    Reúne varias geometrías OpenCascade en un solo compuesto.

    Cada geometría conserva la posición y orientación que ya
    tiene aplicada en el documento.
    """

    compuesto = TopoDS_Compound()
    constructor = BRep_Builder()

    constructor.MakeCompound(
        compuesto
    )

    cantidad = 0

    for geometria in geometrias:
        if geometria is None:
            continue

        if geometria.IsNull():
            continue

        constructor.Add(
            compuesto,
            geometria,
        )
        cantidad += 1

    if cantidad == 0:
        raise ValueError(
            "El proyecto no contiene geometrías "
            "válidas para exportar."
        )

    return compuesto, cantidad


def exportar_proyecto_step(
    geometrias,
    archivo,
):
    """
    Exporta varias geometrías en un solo archivo STEP.

    El resultado se importa en otros programas CAD como
    una pieza multicuerpo o un conjunto de sólidos.
    """

    compuesto, cantidad = crear_compuesto(
        geometrias
    )

    ruta = exportar_step(
        compuesto,
        archivo,
    )

    return ruta, cantidad