# Comparación Weber: FLOWPanel y geometría WingCAD

**Estudio independiente con tres resoluciones:** [INDEPENDENT.md](INDEPENDENT.md).
Usa el ejemplo 08 y Gmsh, sin copiar nodos de referencia. Resultados en
`independent/comparison/report.html`: CL muestra poca variación media→fina,
pero CD todavía no converge. La diferencia residual no puede atribuirse solo al CAD.

**Comparación con discretización igualada:** consulta [MATCHED.md](MATCHED.md).
El ejemplo 09 y `matched_comparison/report.html` reproducen el mismo problema
discreto del tutorial. Los casos descritos abajo conservan la comparación
anterior con Gmsh; no son la reproducción exacta solicitada.

Referencia: https://flow.byu.edu/FLOWPanel.jl/stable/examples/sweptwing-4p2aoa/

Condiciones: 30 m/s, 4.2°, densidad 1.225 kg/m³. Geometría nominal: envergadura
2.4892 m, cuerda constante 0.49784 m, área de referencia 1.239223328 m²,
alargamiento 5, flecha de borde de ataque 45°, sin torsión ni diedro, RAE101 12%.

## Casos

- `reference`: ejemplo adjunto, ejecutado con FLOWPanel 2.0.0, 2880 triángulos,
  15 divisiones por semienvergadura y 24 por cara del perfil. Dos semialas con
  puntas abiertas, estela rígida y sistema directo. Se desactivaron las ventanas
  y se añadieron exportación VTK y coeficientes; no se alteró su discretización.
- `wingcad`: proyecto `examples/08_weber_swept_wing.wingcad`, reconstruido mediante
  WingBuilder/OpenCascade, exportado a STEP y mallado en Gmsh. Sólido cerrado,
  6318 triángulos, sistema de mínimos cuadrados. Es un control adicional, no una
  reproducción de las condiciones de borde de las puntas de la referencia.
- `wingcad_open_tips`: misma malla CAD, retirando solamente las dos tapas de punta,
  6214 triángulos y sistema directo, para igualar el tratamiento de puntas del tutorial.
  No modifica el proyecto CAD. La superficie abierta se usa solo para este benchmark.

Todos usan FLOWPanel como solver. Se comparan dos rutas de generación geométrica
y mallado, no dos solvers independientes. Persisten diferencias de interpolación
del perfil, malla estructurada/no estructurada, distribución y número de paneles,
y una semiala por cuerpo frente a una superficie conectada. No se ha establecido
convergencia. La concordancia con la referencia no equivale a validación experimental.

La interpolación de WingCAD conserva las coordenadas RAE101 distribuidas por
FLOWPanel. Se comprobó simetría y ausencia de cruce de las superficies en 10001
posiciones del perfil; la geometría y topología del sólido pasan los controles del
preparador. La malla cerrada tiene calidad mínima minSICN de 0.3432.

## Resultados de la comparación

| Caso | Paneles | CL | CD inviscido |
|---|---:|---:|---:|
| Referencia FLOWPanel | 2880 | 0.271561 | 0.006598 |
| WingCAD con puntas abiertas | 6214 | 0.250462 | 0.011033 |
| WingCAD sólido cerrado | 6318 | 0.250611 | 0.011898 |
| Experimental (datos distribuidos con el tutorial) | — | 0.238 | 0.005 |

La referencia ejecutada reproduce los valores redondeados de la página oficial.
El caso CAD con puntas abiertas difiere en -7.77 % de CL y +67.22 % de CD respecto
a esa referencia. El sólido cerrado difiere en -7.71 % y +80.33 %, respectivamente.
Igualar las puntas no elimina la discrepancia. Los cortes de presión de la malla
Gmsh presentan oscilaciones locales que se conservan en las gráficas, sin suavizado.
No puede atribuirse toda la diferencia a OpenCascade: también cambian el perfil
interpolado, el mallado, la conexión central y la reconstrucción de velocidades
sobre paneles distintos. La resistencia requiere especial revisión.

FLOWPanel emitió una advertencia de winding numbers en la superficie de puntas
abiertas, indicando que la comprobación de interior/exterior no es concluyente
para una superficie no cerrada. Se conservó la orientación de la malla cerrada
original; no se ignoraron errores de ejecución ni valores no finitos.

El informe visual está en `exports/flowpanel/weber/comparison/report.html`.
Los resultados del caso principal pueden verse en WingCAD abriendo
`exports/flowpanel/weber/wingcad_open_tips/case.toml` y pulsando **View results**.

## Reproducción desde PowerShell

Desde la raíz de WingCAD, con los entornos ya instalados:

```powershell
$py = "C:\Users\PERSONAL\miniconda3\envs\wingcad\python.exe"
$jl = "$env:LOCALAPPDATA\Programs\Julia\julia-1.11.9\bin\julia.exe"
& $jl --startup-file=no --project=analysis/flowpanel analysis/flowpanel/sweptwing/reference.jl exports/flowpanel/weber/reference
& $py analysis/flowpanel/sweptwing/prepare.py
& $jl --startup-file=no --project=analysis/flowpanel analysis/flowpanel/solve.jl exports/flowpanel/weber/wingcad
& $py analysis/flowpanel/sweptwing/match_tips.py
& $jl --startup-file=no --project=analysis/flowpanel analysis/flowpanel/solve.jl exports/flowpanel/weber/wingcad_open_tips
& $py analysis/flowpanel/sweptwing/compare.py
```

Las salidas existentes están protegidas: estos comandos de cálculo son para una
ejecución nueva. El último comando puede repetirse para regenerar las gráficas.
El perfil RAE101 puede editarse en WingCAD escribiendo `RAE101` como perfil de
raíz y punta. El botón general Prepare mesh sigue siendo el adaptador del Manta;
para este benchmark se utiliza el preparador dedicado anterior.
Los casos resultantes pueden abrirse con Open case y View results en WingCAD.

## Gráficas y datos

En `exports/flowpanel/weber/comparison/`:

- `pressure_top_bottom.png`: superior e inferior, misma escala Cp [-0.5, 0.5].
- `chordwise_cp.png` y `pressure_sections.csv`: cortes a 2y/b = .041, .163, .245, .510.
- `delta_cp.png`: Cp superior menos inferior, en nueve estaciones.
- `spanwise_loading.png` y `.csv`: cargas por franjas de envergadura.
- `coefficients.json`: fuerzas integradas verificadas contra cada salida TOML.

Los cortes son intersecciones geométricas a y constante con valores Cp por panel;
no son exactamente el método de columna más próxima del gráfico del tutorial.
Delta Cp utiliza interpolación lineal solo dentro del intervalo común de ambas caras.
Las cargas usan 30 franjas iguales: se recortan los triángulos por franja y se
distribuye su fuerza proporcionalmente al área. Se comprueba conservación de la
fuerza total. El gráfico del tutorial usa sus propias franjas estructuradas.
La representación con colores limitados no cambia los valores guardados.

## Datos y atribución

`reference.jl` deriva del ejemplo de Eduardo J. Alvarez suministrado por el usuario.
Los CSV Weber y `experimental.json` proceden de los datos del ejemplo de FLOWPanel
2.0.0; este último registra la huella del archivo de procedencia. Las presiones
por cara y cargas son las tablas Weber/Brebner que incluye el paquete; los CSV
de diferencia de presión son los archivos denominados `weber1958-fig2-*` del mismo
paquete. No se han digitalizado a ojo las capturas ni se ha revisado el informe
experimental original. Se conserva la [licencia MIT](FLOWPanel-LICENSE.txt).

La ejecución inicial con interpolación de salida defectuosa se conserva en
`wingcad_initial_interpolation` para trazabilidad y está excluida de la comparación.
