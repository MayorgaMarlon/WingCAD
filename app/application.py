"""Modelo principal de la aplicación aeronáutica."""

import json
from pathlib import Path

from app.document import CADDocument
from app.registry import ComponentRegistry
from components.fuselage import FuselageComponent
from components.nacelle import NacelleComponent
from components.wing import WingComponent
from core.fuselage_parameters import FuselageParameters
from core.parameters import WingParameters
from geometry.placement import Placement


class AeroApplication:
    """
    Administra el documento y los componentes disponibles.
    """

    def __init__(self):
        self.registro = ComponentRegistry()
        self.documento = CADDocument()

        self._registrar_componentes_base()

    def _registrar_componentes_base(self):
        """Registra los componentes incluidos inicialmente."""

        self.registro.registrar(
            clave="wing",
            clase=WingComponent,
            etiqueta="Ala",
            categoria="Superficies sustentadoras",
        )

        self.registro.registrar(
            clave="fuselage",
            clase=FuselageComponent,
            etiqueta="Fuselaje",
            categoria="Cuerpos aerodinámicos",
        )
        self.registro.registrar(
            clave="nacelle",
            clase=NacelleComponent,
            etiqueta="Góndola",
            categoria="Propulsión",
        )
    def nuevo_documento(
        self,
        nombre="Proyecto aeronáutico",
    ):
        """Crea un documento vacío."""

        self.documento = CADDocument(nombre)

        return self.documento

    def crear_componente(
        self,
        clave,
        agregar_al_documento=True,
        **argumentos,
    ):
        """Crea un objeto usando el registro."""

        objeto = self.registro.crear(
            clave,
            **argumentos,
        )

        if agregar_al_documento:
            self.documento.agregar_objeto(objeto)

        return objeto

    def recalcular_documento(self):
        """Recalcula los objetos modificados."""

        return self.documento.recalcular()

    def obtener_componentes_disponibles(self):
        """Devuelve los tipos disponibles para la interfaz."""

        return self.registro.listar()

    def guardar_proyecto(self, ruta):
        """Guarda el documento paramétrico en formato .wingcad."""

        ruta = Path(ruta)

        if ruta.suffix.lower() != ".wingcad":
            ruta = ruta.with_suffix(".wingcad")

        datos = {
            "formato": "WingCAD",
            "version": 1,
            "documento": {
                "nombre": self.documento.nombre,
                "objetos": [
                    self._serializar_objeto(objeto)
                    for objeto in self.documento.objetos
                ],
            },
        }

        ruta.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        ruta.write_text(
            json.dumps(
                datos,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        self.documento.marcar_guardado()

        return ruta

    def abrir_proyecto(self, ruta):
        """Carga un proyecto sin dañar el documento actual si hay error."""

        ruta = Path(ruta)

        try:
            datos = json.loads(
                ruta.read_text(encoding="utf-8")
            )
        except OSError as error:
            raise RuntimeError(
                f"No se pudo leer el proyecto: {error}"
            ) from error
        except json.JSONDecodeError as error:
            raise ValueError(
                "El archivo no contiene un proyecto WingCAD válido."
            ) from error

        if (
            not isinstance(datos, dict)
            or datos.get("formato") != "WingCAD"
        ):
            raise ValueError(
                "El archivo no corresponde a un proyecto WingCAD."
            )

        if datos.get("version") != 1:
            raise ValueError(
                "La versión del proyecto no es compatible."
            )

        datos_documento = datos.get("documento")

        if not isinstance(datos_documento, dict):
            raise ValueError(
                "Falta la información del documento."
            )

        nombre = datos_documento.get(
            "nombre",
            "Proyecto aeronáutico",
        )
        objetos = datos_documento.get("objetos")

        if not isinstance(nombre, str) or not nombre.strip():
            raise ValueError(
                "El nombre del documento no es válido."
            )

        if not isinstance(objetos, list):
            raise ValueError(
                "La lista de objetos del proyecto no es válida."
            )

        documento_nuevo = CADDocument(nombre.strip())

        for datos_objeto in objetos:
            objeto = self._restaurar_objeto(datos_objeto)
            documento_nuevo.agregar_objeto(objeto)

        errores = documento_nuevo.recalcular()

        if errores:
            mensajes = "\n".join(
                error["mensaje"]
                for error in errores
            )
            raise RuntimeError(
                "No se pudo reconstruir el proyecto guardado:\n"
                f"{mensajes}"
            )

        documento_nuevo.marcar_guardado()
        self.documento = documento_nuevo

        return documento_nuevo

    @staticmethod
    def _serializar_objeto(objeto):
        """Convierte un componente paramétrico en datos JSON."""

        if isinstance(objeto, WingComponent):
            clave = "wing"
        elif isinstance(objeto, FuselageComponent):
            clave = "fuselage"
        elif isinstance(objeto, NacelleComponent):
            clave = "nacelle"
        else:
            raise TypeError(
                f"No se puede guardar el tipo "
                f"{type(objeto).__name__}."
            )

        datos = {
            "id": objeto.id,
            "clave": clave,
            "nombre": objeto.nombre,
            "visible": objeto.visible,
            "placement": objeto.placement.como_diccionario(),
            "densidad_kg_m3": objeto.densidad_kg_m3,
            "modelo_masa": objeto.modelo_masa,
            "espesor_mm": objeto.espesor_mm,
            "parametros": objeto.obtener_parametros(),  
        }

        if isinstance(objeto, WingComponent):
            datos["modo_superficie"] = objeto.modo_superficie

        return datos

    @staticmethod
    def _restaurar_objeto(datos):
        """Crea un componente a partir de una entrada del proyecto."""

        if not isinstance(datos, dict):
            raise ValueError(
                "Un objeto guardado no tiene un formato válido."
            )

        clave = datos.get("clave")
        nombre = datos.get("nombre")
        identificador = datos.get("id")
        parametros = datos.get("parametros")
        densidad = datos.get("densidad_kg_m3")
        modelo_masa = datos.get(
            "modelo_masa",
            "solido",
        )
        espesor_mm = datos.get(
            "espesor_mm",
            2.0,
        )
        placement = Placement.desde_diccionario(
            datos.get("placement", {})
        )

        if not isinstance(nombre, str) or not nombre.strip():
            raise ValueError(
                "Un objeto guardado no tiene nombre válido."
            )

        if not isinstance(parametros, dict):
            raise ValueError(
                f"Los parámetros de '{nombre}' no son válidos."
            )

        if clave == "wing":
            objeto = WingComponent(
                nombre=nombre.strip(),
                parametros=WingParameters(**parametros),
                densidad=densidad,
                placement=placement,
                modo_superficie=datos.get(
                    "modo_superficie",
                    "simetrica",
                ),
                modelo_masa=modelo_masa,
                espesor_mm=espesor_mm,
            )

        elif clave == "fuselage":
            objeto = FuselageComponent(
                nombre=nombre.strip(),
                parametros=FuselageParameters(**parametros),
                densidad=densidad,
                placement=placement,
                modelo_masa=modelo_masa,
                espesor_mm=espesor_mm,
            )
        elif clave == "nacelle":
            objeto = NacelleComponent(
                nombre=nombre.strip(),
                parametros=NacelleParameters(
                    **parametros
                ),
                densidad=densidad,
                placement=placement,
                modelo_masa=modelo_masa,
                espesor_mm=espesor_mm,
            )
        else:
            raise ValueError(
                f"El tipo de componente '{clave}' no es compatible."
            )

        objeto.restaurar_id(identificador)
        objeto.establecer_visibilidad(
            datos.get("visible", True)
        )

        return objeto   