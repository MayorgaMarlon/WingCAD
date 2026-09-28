"""Generación matemática de perfiles NACA de cuatro dígitos."""

import math

from OCP.gp import gp_Pnt


def puntos_naca4(codigo="2412", cuerda=1000.0, numero_puntos=60):
    """
    Genera las superficies superior e inferior de un perfil NACA 4 dígitos.

    Parámetros
    ----------
    codigo:
        Código NACA, por ejemplo "2412".
    cuerda:
        Longitud de cuerda en milímetros.
    numero_puntos:
        Cantidad de puntos por superficie.

    Retorna
    -------
    tuple:
        (puntos_superiores, puntos_inferiores)
    """

    if len(codigo) != 4 or not codigo.isdigit():
        raise ValueError("El código NACA debe contener cuatro números.")

    if cuerda <= 0:
        raise ValueError("La cuerda debe ser mayor que cero.")

    if numero_puntos < 10:
        raise ValueError("Se necesitan al menos 10 puntos.")

    # Parámetros del perfil NACA
    m = int(codigo[0]) / 100.0
    p = int(codigo[1]) / 10.0
    t = int(codigo[2:]) / 100.0

    superficie_superior = []
    superficie_inferior = []

    for indice in range(numero_puntos):
        beta = math.pi * indice / (numero_puntos - 1)

        # Distribución cosenoidal: más puntos cerca del borde de ataque
        x = 0.5 * (1.0 - math.cos(beta))

        # Distribución de espesor con borde de salida cerrado
        yt = 5.0 * t * (
            0.2969 * math.sqrt(x)
            - 0.1260 * x
            - 0.3516 * x**2
            + 0.2843 * x**3
            - 0.1036 * x**4
        )

        # Línea media y su pendiente
        if m == 0.0 or p == 0.0:
            yc = 0.0
            pendiente = 0.0

        elif x < p:
            yc = (m / p**2) * (2.0 * p * x - x**2)
            pendiente = (2.0 * m / p**2) * (p - x)

        else:
            yc = (
                m / (1.0 - p) ** 2
                * ((1.0 - 2.0 * p) + 2.0 * p * x - x**2)
            )
            pendiente = (
                2.0 * m / (1.0 - p) ** 2
                * (p - x)
            )

        theta = math.atan(pendiente)

        xu = x - yt * math.sin(theta)
        zu = yc + yt * math.cos(theta)

        xl = x + yt * math.sin(theta)
        zl = yc - yt * math.cos(theta)

        # El perfil se encuentra inicialmente en el plano X-Z
        superficie_superior.append(
            gp_Pnt(xu * cuerda, 0.0, zu * cuerda)
        )

        superficie_inferior.append(
            gp_Pnt(xl * cuerda, 0.0, zl * cuerda)
        )

    return superficie_superior, superficie_inferior