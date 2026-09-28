"""Documento general de la aplicación CAD."""

from collections import OrderedDict


class CADDocument:
    """
    Contiene y administra todos los componentes del proyecto.

    Funciona como el documento de un programa CAD:
    guarda objetos, controla su orden y los recalcula.
    """

    def __init__(self, nombre="Proyecto aeronáutico"):
        self.nombre = nombre
        self._objetos = OrderedDict()
        self.modificado = False

    @property
    def objetos(self):
        """Devuelve los objetos respetando su orden."""

        return tuple(self._objetos.values())

    def agregar_objeto(self, objeto):
        """Agrega un objeto paramétrico al documento."""

        if objeto.id in self._objetos:
            raise ValueError(
                "El objeto ya pertenece al documento."
            )

        self._objetos[objeto.id] = objeto
        self.modificado = True

        return objeto

    def eliminar_objeto(self, identificador):
        """Elimina un objeto mediante su identificador."""

        if identificador not in self._objetos:
            raise KeyError(
                "No existe un objeto con ese identificador."
            )

        objeto = self._objetos.pop(identificador)
        self.modificado = True

        return objeto

    def obtener_objeto(self, identificador):
        """Busca un objeto mediante su identificador."""

        return self._objetos.get(identificador)

    def buscar_por_nombre(self, nombre):
        """Busca el primer objeto que tenga el nombre indicado."""

        for objeto in self._objetos.values():
            if objeto.nombre == nombre:
                return objeto

        return None

    def recalcular(self):
        """
        Reconstruye únicamente los objetos modificados.

        Devuelve una lista con los errores encontrados.
        """

        errores = []

        for objeto in self._objetos.values():
            if not objeto.modificado:
                continue

            try:
                objeto.recalcular()

            except Exception as error:
                errores.append(
                    {
                        "objeto": objeto,
                        "mensaje": str(error),
                    }
                )

        if not errores:
            self.modificado = False

        return errores

    def obtener_geometrias_visibles(self):
        """Devuelve las geometrías válidas y visibles."""

        geometrias = []

        for objeto in self._objetos.values():
            if (
                objeto.visible
                and objeto.valido
                and objeto.shape is not None
            ):
                geometrias.append(
                    {
                        "objeto": objeto,
                        "shape": objeto.shape,
                    }
                )

        return geometrias

    def limpiar(self):
        """Vacía el documento."""

        self._objetos.clear()
        self.modificado = True

    def marcar_guardado(self):
        """Indica que el documento fue guardado."""

        self.modificado = False

    def calcular_propiedades_globales(self):
        """
        Calcula masa, centro de gravedad e inercias del ensamblaje.

        Las inercias se calculan respecto al centro de gravedad
        global mediante el teorema de ejes paralelos.
        """

        componentes = []
        masa_total = 0.0

        suma_mx = 0.0
        suma_my = 0.0
        suma_mz = 0.0

        for objeto in self._objetos.values():
            propiedades = getattr(
                objeto,
                "propiedades",
                None,
            )

            if (
                not objeto.valido
                or propiedades is None
            ):
                continue

            masa = float(
                propiedades.masa_kg
            )

            if masa <= 0.0:
                continue

            componente = {
                "id": objeto.id,
                "nombre": objeto.nombre,
                "tipo": objeto.tipo,
                "masa_kg": masa,
                "cg_x_mm": float(
                    propiedades.cg_x_mm
                ),
                "cg_y_mm": float(
                    propiedades.cg_y_mm
                ),
                "cg_z_mm": float(
                    propiedades.cg_z_mm
                ),
                "inercia_xx_kg_m2": float(
                    propiedades.inercia_xx_kg_m2
                ),
                "inercia_yy_kg_m2": float(
                    propiedades.inercia_yy_kg_m2
                ),
                "inercia_zz_kg_m2": float(
                    propiedades.inercia_zz_kg_m2
                ),
            }

            componentes.append(componente)

            masa_total += masa
            suma_mx += masa * componente["cg_x_mm"]
            suma_my += masa * componente["cg_y_mm"]
            suma_mz += masa * componente["cg_z_mm"]

        if masa_total <= 0.0:
            return {
                "masa_total_kg": 0.0,
                "cg_x_mm": 0.0,
                "cg_y_mm": 0.0,
                "cg_z_mm": 0.0,
                "inercia_xx_kg_m2": 0.0,
                "inercia_yy_kg_m2": 0.0,
                "inercia_zz_kg_m2": 0.0,
                "componentes": [],
            }

        cg_x_mm = suma_mx / masa_total
        cg_y_mm = suma_my / masa_total
        cg_z_mm = suma_mz / masa_total

        inercia_xx = 0.0
        inercia_yy = 0.0
        inercia_zz = 0.0

        for componente in componentes:
            masa = componente["masa_kg"]

            dx_m = (
                componente["cg_x_mm"] - cg_x_mm
            ) / 1000.0
            dy_m = (
                componente["cg_y_mm"] - cg_y_mm
            ) / 1000.0
            dz_m = (
                componente["cg_z_mm"] - cg_z_mm
            ) / 1000.0

            inercia_xx += (
                componente["inercia_xx_kg_m2"]
                + masa * (dy_m**2 + dz_m**2)
            )
            inercia_yy += (
                componente["inercia_yy_kg_m2"]
                + masa * (dx_m**2 + dz_m**2)
            )
            inercia_zz += (
                componente["inercia_zz_kg_m2"]
                + masa * (dx_m**2 + dy_m**2)
            )

        return {
            "masa_total_kg": masa_total,
            "cg_x_mm": cg_x_mm,
            "cg_y_mm": cg_y_mm,
            "cg_z_mm": cg_z_mm,
            "inercia_xx_kg_m2": inercia_xx,
            "inercia_yy_kg_m2": inercia_yy,
            "inercia_zz_kg_m2": inercia_zz,
            "componentes": componentes,
        }

    def obtener_resumen(self):
        """Devuelve información general del documento."""

        return {
            "nombre": self.nombre,
            "numero_objetos": len(self._objetos),
            "modificado": self.modificado,
            "objetos": [
                objeto.obtener_resumen()
                for objeto in self._objetos.values()
            ],
        }