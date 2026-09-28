"""Visualizador 3D de geometrías OpenCascade mediante VTK."""

from OCP.BRep import BRep_Tool
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.TopAbs import TopAbs_FACE, TopAbs_REVERSED
from OCP.TopExp import TopExp_Explorer
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS

import vtk


def convertir_shape_a_vtk(shape, tolerancia=2.0):
    """Convierte una geometría B-Rep de OpenCascade en una malla VTK."""

    mallador = BRepMesh_IncrementalMesh(
        shape,
        tolerancia,
        False,
        0.5,
        True,
    )
    mallador.Perform()

    puntos_vtk = vtk.vtkPoints()
    triangulos_vtk = vtk.vtkCellArray()

    explorador = TopExp_Explorer(shape, TopAbs_FACE)

    while explorador.More():
        cara = TopoDS.Face_s(explorador.Current())
        ubicacion = TopLoc_Location()

        triangulacion = BRep_Tool.Triangulation_s(
            cara,
            ubicacion,
        )

        if triangulacion is not None:
            transformacion = ubicacion.Transformation()
            indices_globales = {}

            for indice in range(1, triangulacion.NbNodes() + 1):
                punto = triangulacion.Node(indice)
                punto.Transform(transformacion)

                indice_vtk = puntos_vtk.InsertNextPoint(
                    punto.X(),
                    punto.Y(),
                    punto.Z(),
                )

                indices_globales[indice] = indice_vtk

            for indice in range(1, triangulacion.NbTriangles() + 1):
                triangulo = triangulacion.Triangle(indice)
                nodo_1, nodo_2, nodo_3 = triangulo.Get()

                if cara.Orientation() == TopAbs_REVERSED:
                    nodo_2, nodo_3 = nodo_3, nodo_2

                celda = vtk.vtkTriangle()
                celda.GetPointIds().SetId(
                    0,
                    indices_globales[nodo_1],
                )
                celda.GetPointIds().SetId(
                    1,
                    indices_globales[nodo_2],
                )
                celda.GetPointIds().SetId(
                    2,
                    indices_globales[nodo_3],
                )

                triangulos_vtk.InsertNextCell(celda)

        explorador.Next()

    malla = vtk.vtkPolyData()
    malla.SetPoints(puntos_vtk)
    malla.SetPolys(triangulos_vtk)

    normales = vtk.vtkPolyDataNormals()
    normales.SetInputData(malla)
    normales.ComputePointNormalsOn()
    normales.ComputeCellNormalsOn()
    normales.ConsistencyOn()
    normales.AutoOrientNormalsOn()
    normales.NonManifoldTraversalOn()
    normales.SplittingOff()
    normales.Update()
    return normales.GetOutput()


def mostrar_shape(shape, titulo="WingCAD — Ala paramétrica"):
    """Abre una ventana interactiva para visualizar la geometría."""

    malla = convertir_shape_a_vtk(shape)

    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputData(malla)
    mapper.ScalarVisibilityOff()

    actor = vtk.vtkActor()
    actor.SetMapper(mapper)

    # Apariencia del ala
    actor.GetProperty().SetColor(0.82, 0.86, 0.94)
    actor.GetProperty().SetSpecular(0.35)
    actor.GetProperty().SetSpecularPower(25.0)
    actor.GetProperty().SetInterpolationToPhong()
    actor.GetProperty().SetRepresentationToSurface()
    actor.GetProperty().EdgeVisibilityOff()
    actor.GetProperty().SetOpacity(1.0)
    actor.GetProperty().BackfaceCullingOff()
    actor.GetProperty().FrontfaceCullingOff()
    actor.GetProperty().SetLineWidth(0.5)

    renderer = vtk.vtkRenderer()
    renderer.AddActor(actor)
    renderer.SetBackground(0.08, 0.10, 0.14)
    renderer.SetBackground2(0.22, 0.27, 0.34)
    renderer.GradientBackgroundOn()
    renderer.ResetCamera()

    camara = renderer.GetActiveCamera()
    camara.Azimuth(35)
    camara.Elevation(25)
    camara.Zoom(1.1)

    ventana = vtk.vtkRenderWindow()
    ventana.SetWindowName(titulo)
    ventana.SetSize(1100, 700)
    ventana.AddRenderer(renderer)

    interactuador = vtk.vtkRenderWindowInteractor()
    interactuador.SetRenderWindow(ventana)

    estilo = vtk.vtkInteractorStyleTrackballCamera()
    interactuador.SetInteractorStyle(estilo)

    ventana.Render()
    interactuador.Initialize()
    interactuador.Start() 