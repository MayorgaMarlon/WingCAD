"""Exportación de geometrías CAD."""

from pathlib import Path

from OCP.BRep import BRep_Builder
from OCP.IFSelect import IFSelect_RetDone
from OCP.Interface import Interface_Static
from OCP.STEPControl import (
    STEPControl_AsIs,
    STEPControl_Controller,
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
    Reúne varias geometrías en un compuesto.

    Las posiciones y orientaciones aplicadas en WingCAD
    se conservan.
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
    Exporta el proyecto como una sola pieza multicuerpo.

    Se desactiva la estructura STEP de ensamblaje para
    evitar que Inventor cree automáticamente un archivo IAM.
    """

    compuesto, cantidad = crear_compuesto(
        geometrias
    )

    # Registrar los parametros STEP antes de leer su valor inicial.
    if not STEPControl_Controller.Init_s():
        raise RuntimeError("No se pudo inicializar el exportador STEP.")

    configuracion_anterior = (
        Interface_Static.IVal_s(
            "write.step.assembly"
        )
    )

    try:
        if not Interface_Static.SetIVal_s(
            "write.step.assembly",
            0,
        ):
            raise RuntimeError(
                "No se pudo desactivar la estructura de ensamblaje STEP."
            )

        ruta = exportar_step(
            compuesto,
            archivo,
        )
    finally:
        Interface_Static.SetIVal_s(
            "write.step.assembly",
            configuracion_anterior,
        )

    return ruta, cantidad
