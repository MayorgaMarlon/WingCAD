"""Exportación de geometrías CAD."""

from pathlib import Path
from tempfile import TemporaryDirectory

from OCP.BRep import BRep_Builder
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepTools import BRepTools
from OCP.IFSelect import IFSelect_RetDone
from OCP.Interface import Interface_Static
from OCP.STEPControl import (
    STEPControl_AsIs,
    STEPControl_Controller,
    STEPControl_Writer,
)
from OCP.TopoDS import TopoDS_Compound


def _preparar_ruta(archivo):
    """Prepara la carpeta donde se guardará la geometría."""

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


EXPORT_FILTERS = {
    "STEP part (*.step *.stp)": "step",
    "OpenCascade BREP (*.brep)": "brep",
    "STL mesh (*.stl)": "stl",
    "GLB scene (*.glb)": "glb",
    "Wavefront OBJ (*.obj)": "obj",
}


def exportar_geometria(geometria, archivo, nombre="Object"):
    """Export one object, preserving the existing individual STEP behavior."""
    ruta, _ = _exportar([geometria], archivo, [nombre], proyecto=False)
    return ruta


def exportar_proyecto(geometrias, archivo, nombres=None):
    """Export positioned components without fusing them together."""
    return _exportar(geometrias, archivo, nombres, proyecto=True)


def _exportar(geometrias, archivo, nombres, proyecto):
    shapes = list(geometrias)
    names = list(nombres) if nombres is not None else [
        f"Component {i + 1}" for i in range(len(shapes))
    ]
    if len(names) != len(shapes):
        raise ValueError("Each component must have one name.")
    pairs = [(s, str(n)) for s, n in zip(shapes, names)
             if s is not None and not s.IsNull()]
    if not pairs or (not proyecto and len(pairs) != 1):
        raise ValueError("There is no valid geometry to export.")
    shapes, names = map(list, zip(*pairs))
    if any(not BRepCheck_Analyzer(s).IsValid() for s in shapes):
        raise ValueError("Invalid geometry cannot be exported. Rebuild the component first.")
    suffix = Path(archivo).suffix.lower()
    if suffix not in (".step", ".stp", ".brep", ".stl", ".glb", ".obj"):
        raise ValueError("Choose STEP, BREP, STL, GLB or OBJ.")
    path = _preparar_ruta(archivo).resolve()
    # Write beside the destination, then replace only after a successful export.
    # GLB writers may create intermediate files; keep them in the same temp folder.
    with TemporaryDirectory(prefix=".wingcad-export-", dir=path.parent) as folder:
        temporary = Path(folder) / ("model" + suffix)
        if suffix in (".step", ".stp"):
            if proyecto:
                exportar_proyecto_step(shapes, temporary)
            else:
                exportar_step(shapes[0], temporary)
        elif suffix == ".brep":
            shape = crear_compuesto(shapes)[0] if proyecto else shapes[0]
            if not BRepTools.Write_s(shape, str(temporary)):
                raise RuntimeError("Unable to write the BREP file.")
        else:
            from core.mesh_exporter import write_glb, write_obj, write_stl
            if suffix == ".stl":
                write_stl(crear_compuesto(shapes)[0], temporary)
            elif suffix == ".glb":
                write_glb(shapes, names, temporary)
            else:
                write_obj(shapes, names, temporary)
        if not temporary.is_file() or temporary.stat().st_size == 0:
            raise RuntimeError("The exporter did not produce a file.")
        temporary.replace(path)
    return path, len(shapes)
