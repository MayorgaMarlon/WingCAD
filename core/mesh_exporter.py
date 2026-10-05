"""Mesh file writers using OpenCascade only; no GUI or VTK dependency."""

from OCP.BRep import BRep_Tool
from OCP.BRepBuilderAPI import BRepBuilderAPI_Copy
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.Message import Message_ProgressRange
from OCP.RWGltf import RWGltf_CafWriter
from OCP.RWMesh import RWMesh_CoordinateSystem_Zup, RWMesh_CoordinateSystem_Yup
from OCP.StlAPI import StlAPI_Writer
from OCP.TCollection import TCollection_AsciiString, TCollection_ExtendedString
from OCP.TColStd import TColStd_IndexedDataMapOfStringString
from OCP.TDataStd import TDataStd_Name
from OCP.TDocStd import TDocStd_Document
from OCP.TopAbs import TopAbs_FACE, TopAbs_REVERSED
from OCP.TopExp import TopExp_Explorer
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS
from OCP.XCAFDoc import XCAFDoc_DocumentTool


def _mesh(shape):
    # Do not replace the document's display triangulation with an export mesh.
    copied = BRepBuilderAPI_Copy(shape, True, False).Shape()
    mesher = BRepMesh_IncrementalMesh(copied, 0.5, False, 0.2, False)
    if not mesher.IsDone():
        raise RuntimeError("Unable to triangulate the geometry.")
    faces = TopExp_Explorer(copied, TopAbs_FACE)
    count = 0
    while faces.More():
        face = TopoDS.Face_s(faces.Current())
        triangulation = BRep_Tool.Triangulation_s(face, TopLoc_Location())
        if triangulation is None or triangulation.NbTriangles() == 0:
            raise RuntimeError("A face could not be triangulated for export.")
        count += triangulation.NbTriangles()
        faces.Next()
    if not count:
        raise ValueError("The geometry contains no surfaces to export as a mesh.")
    return copied


def write_stl(shape, path):
    writer = StlAPI_Writer()
    writer.ASCIIMode = False
    if not writer.Write(_mesh(shape), str(path)):
        raise RuntimeError("Unable to write the STL file.")


def write_glb(shapes, names, path):
    document = TDocStd_Document(TCollection_ExtendedString("BinXCAF"))
    shape_tool = XCAFDoc_DocumentTool.ShapeTool_s(document.Main())
    for shape, name in zip(shapes, names):
        label = shape_tool.AddShape(_mesh(shape), False)
        TDataStd_Name.Set_s(label, TCollection_ExtendedString(name))
    writer = RWGltf_CafWriter(TCollection_AsciiString(str(path)), True)
    converter = writer.ChangeCoordinateSystemConverter()
    converter.SetInputCoordinateSystem(RWMesh_CoordinateSystem_Zup)
    converter.SetOutputCoordinateSystem(RWMesh_CoordinateSystem_Yup)
    converter.SetInputLengthUnit(0.001)
    converter.SetOutputLengthUnit(1.0)
    if not writer.Perform(document, TColStd_IndexedDataMapOfStringString(),
                          Message_ProgressRange()):
        raise RuntimeError("Unable to write the GLB file.")


def write_obj(shapes, names, path):
    # OBJ is unitless; retain WingCAD's millimeter coordinates and Z-up axes.
    offset = 0
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write("# WingCAD OBJ: coordinates in millimeters; Z up\n")
        for index, (shape, name) in enumerate(zip(shapes, names), 1):
            safe_name = "".join(c if c.isalnum() or c in "_-" else "_" for c in name)
            stream.write(f"o {index}_{safe_name}\n")
            faces = TopExp_Explorer(_mesh(shape), TopAbs_FACE)
            while faces.More():
                face = TopoDS.Face_s(faces.Current())
                location = TopLoc_Location()
                mesh = BRep_Tool.Triangulation_s(face, location)
                transform = location.Transformation()
                for node in range(1, mesh.NbNodes() + 1):
                    point = mesh.Node(node).Transformed(transform)
                    stream.write(f"v {point.X():.12g} {point.Y():.12g} {point.Z():.12g}\n")
                reversed_face = (face.Orientation() == TopAbs_REVERSED) != transform.IsNegative()
                for triangle in range(1, mesh.NbTriangles() + 1):
                    a, b, c = mesh.Triangle(triangle).Get()
                    if reversed_face:
                        b, c = c, b
                    stream.write(f"f {a + offset} {b + offset} {c + offset}\n")
                offset += mesh.NbNodes()
                faces.Next()
