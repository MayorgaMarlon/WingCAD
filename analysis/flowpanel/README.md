# WingCAD → Gmsh → FLOWPanel: Manta

## Uso desde WingCAD

La pestaña **Analysis / FLOWPanel**, junto a **Design**, reúne el flujo:

1. Abre `examples/02_manta_uav.wingcad` y aplica los cambios del modelo.
2. Selecciona **Complete aircraft** o **Wing only**, y la resolución.
3. Pulsa **Prepare mesh**. Se guarda una copia de los parámetros actuales y
   se ejecuta Gmsh en segundo plano; el documento abierto no se marca como guardado.
4. **View mesh** muestra los triángulos en el visor 3D de la misma pestaña.
5. **Configure simulation** permite editar velocidad, ángulo de ataque y densidad.
6. **Run simulation** ejecuta Julia sin bloquear la interfaz. Cada ejecución usa
   una carpeta nueva dentro de `runs/`; conserva las mallas y resultados anteriores.
7. Al terminar se muestran CL, CD inviscido, Cm y la presión en el visor integrado.
   **View results** vuelve a mostrar los resultados del caso seleccionado.

El visor permite girar y ampliar el modelo, mostrar aristas, activar la estela,
ajustar la cámara y usar el rango completo de Cp o limitar los colores a [-1.2, 1].
El rango limitado satura los colores extremos, sin modificar los datos.
**Open case** permite seleccionar el `case.toml` de una malla o simulación anterior,
incluido `exports/flowpanel/manta/aircraft/coarse/case.toml` para ver el primer resultado.

La sección **Task log** muestra la salida y los errores; **Cancel task** detiene
el proceso. Una tarea cancelada puede dejar archivos incompletos, que no deben usarse.
La ventana principal no se cierra mientras haya una tarea activa: espera o cancélala.
Julia se busca en PATH y en la instalación local; puede seleccionarse otro ejecutable.

El adaptador sigue limitado al Manta: un ala simétrica sin rotación y un cuerpo
central. No convierte automáticamente los demás ejemplos. Los bordes de salida
deben superar la identificación geométrica antes de publicar la malla.
Las tareas se guardan en `exports/flowpanel/gui/`; cambios posteriores en el diseño
no modifican una malla existente. Las mallas de más de 8000 paneles se pueden ver,
pero el panel no permite simularlas. Las referencias se muestran al cargar el caso.

Verificación de esta integración: compilación Python e importación de los módulos
de análisis sin crear QApplication ni cargar VTK. La interacción gráfica del nuevo
panel requiere comprobación manual; no se inició la interfaz desde el agente.

Esta integración es una primera implementación, pendiente de prueba de extremo
a extremo. Se generaron las seis mallas del Manta (ala y avión completo, con
tres resoluciones). Se ejecutó el primer caso del avión completo con malla gruesa.
Julia 1.11.9 está instalado en Windows y Gmsh 4.15.2 está disponible en el
entorno `wingcad`. Se verificaron correctamente las importaciones de FLOWPanel
2.0.0, Meshes 0.42.2, GeoIO 1.12.15 y Gmsh. No hace falta instalar Ubuntu/WSL
para utilizar esta instalación. El flujo completo de mallado y simulación
todavía requiere validación aerodinámica.

## Mallas generadas

| Geometría | Gruesa | Media | Fina |
|---|---:|---:|---:|
| Ala | 3492 | 7188 | 17802 |
| Avión completo | 3410 | 7040 | 17452 |

Los valores son números de triángulos superficiales. Los seis casos pasaron
las comprobaciones de cierre, orientación, ausencia de triángulos duplicados
o degenerados y pertenencia de los bordes de salida a la superficie.
Están en `exports/flowpanel/manta/{wing,aircraft}/{coarse,medium,fine}/`.
La vista previa está en `exports/flowpanel/manta/aircraft/coarse/mesh_preview.png`.
Las dos mallas finas superan el límite predeterminado de 8000 paneles del solver.
Estos controles no demuestran convergencia ni validación aerodinámica.

FLOWPanel leyó los seis casos y confirmó el número de paneles. Identificó
102/152/242 segmentos de salida en el ala y 88/132/210 en el avión completo
(gruesa/media/fina). Para repetir la comprobación de un caso, sin resolverlo:

```powershell
& "$env:LOCALAPPDATA\Programs\Julia\julia-1.11.9\bin\julia.exe" --startup-file=no --project=analysis/flowpanel analysis/flowpanel/check_meshes.jl exports/flowpanel/manta/aircraft/coarse
```

## 1. Instalar las herramientas

El mallado se prepara con el Python de WingCAD en Windows. Para usar la
instalación local de Julia desde PowerShell, define su ruta en cada terminal:

```powershell
cd "C:\Users\PERSONAL\Desktop\WingCAD"
$juliaExe = "$env:LOCALAPPDATA\Programs\Julia\julia-1.11.9\bin\julia.exe"
& $juliaExe --version
& $juliaExe --startup-file=no --project=analysis/flowpanel analysis/flowpanel/check_install.jl
```

`check_install.jl` comprueba importaciones y sintaxis, sin generar mallas ni
ejecutar simulaciones. No se ha modificado el PATH. Para restaurar las versiones
del manifiesto en una instalación nueva:

```powershell
& $juliaExe --startup-file=no --project=analysis/flowpanel -e 'import Pkg; Pkg.instantiate()'
```

En **PowerShell**, desde la carpeta WingCAD:

```powershell
cd "C:\Users\PERSONAL\Desktop\WingCAD"
& "C:\Users\PERSONAL\miniconda3\envs\wingcad\python.exe" -m pip install -r analysis\flowpanel\requirements.txt
```

Ese comando instala Gmsh 4.15.2 y su API Python. No hace falta abrir su interfaz.
Se usan también NumPy, SciPy y OCP, que ya forman parte del entorno de WingCAD.

`setup.jl` descarga FLOWPanel, Meshes y GeoIO usando el gestor de paquetes de
Julia cuando todavía no existe un entorno. Conserva el `Project.toml` y
`Manifest.toml` generados: fijan las versiones
que se deberán usar para reproducir los casos. El API de los scripts sigue los
tutoriales oficiales, pero su compatibilidad debe confirmarse en esta primera ejecución.

ParaView es opcional para abrir los resultados VTK; ningún script lo inicia.
FLOWPanel no requiere FreeCAD, AeroShape ni GPU para este caso.
La dependencia CondaPkg gestiona su propio Python bajo `.CondaPkg/`, excluido
de Git, sin cambiar el entorno Python `wingcad`.

## 2. Preparar primero el ala

En **PowerShell**:

```powershell
& "C:\Users\PERSONAL\miniconda3\envs\wingcad\python.exe" analysis\flowpanel\prepare.py --mode wing --level coarse
```

Este paso reconstruye el ala con OpenCascade, exporta un STEP temporal y crea
una malla superficial triangular con Gmsh, sin QApplication ni visualizador VTK.
Es una ejecución geométrica real, no una mera prueba de importación.

Salida: `exports/flowpanel/manta/wing/coarse/`:

- `analysis.step`: geometría de análisis en milímetros.
- `surface.msh`: malla superficial MSH 4.1 ASCII, ya en metros.
- `te_left.msh`, `te_right.msh`: bordes de salida discretizados, en metros.
- `case.toml`: parámetros, referencias, huella del proyecto y auditoría de malla.

Se comprueba validez CAD, un único sólido, triángulos no degenerados ni duplicados,
dos paneles por arista, orientación consistente y pertenencia de los segmentos
del borde de salida a la malla superficial. La identificación LE/TE es geométrica
y específica del Manta actual; si falla se detiene, no se inventan etiquetas.
Estas comprobaciones no sustituyen la inspección de la superficie y de la estela.

## 3. Resolver el caso inicial

El caso `aircraft/coarse` ya se resolvió con FLOWPanel 2.0.0: 3410 paneles,
88 segmentos de salida, 20 m/s, 4° y densidad de 1.225 kg/m³.
Resultados preliminares: CL = 0.1509374, CD inviscido = 0.0109166,
Cm = -0.0187456 respecto a `[0.9, 0, 0]` m. Sustentación: 266.25 N;
resistencia inviscida: 19.26 N. Tiempo del solver: 3.85 s (excluye carga,
preparación y posproceso).

Los archivos están en `exports/flowpanel/manta/aircraft/coarse/results/`:
`coefficients.toml`, `manta.vtk`, `manta_wake.vtk`, `verification.json` y
`pressure_cp.pos`. Este último permite ver Cp en 3D abriéndolo en Gmsh.
Se comprobaron 3410 valores por campo, todos finitos, y se verificó que la
suma de fuerzas del VTK reproduce CL y CD. Cp varía entre -7.463 y 0.911;
el mínimo está cerca de `[2.4202, 0.3890, 0.0067]` m y requiere revisión local.
La fuerza lateral es 2.54 N pese a la geometría simétrica: debe revisarse junto
con la sensibilidad a la malla. No se ha demostrado convergencia ni validado
la distribución de presión o la estela. CD inviscido no es resistencia total.
No vuelvas a resolver ese mismo directorio: el script protege los resultados
existentes. Usa otra resolución o una nueva carpeta de caso.

En **PowerShell**, desde el mismo proyecto y con `$juliaExe` definido:

```powershell
& $juliaExe --startup-file=no --project=analysis/flowpanel analysis/flowpanel/solve.jl exports/flowpanel/manta/wing/coarse
```

Condiciones iniciales editables en `case.toml`: 20 m/s, 4 grados y 1.225 kg/m³.
Son condiciones de prueba, no un punto de vuelo validado. La superficie de
referencia es el área trapezoidal bruta del ala; la cuerda de referencia es la
cuerda aerodinámica media de ese trapecio. El momento se calcula respecto al
punto explícito `[0.9, 0, 0]` m, no a un centro aerodinámico calculado.

Se utiliza el solver de mínimos cuadrados para cuerpo cerrado, estela rígida
alineada con la corriente y CPU. La orientación se obtiene del volumen firmado
de la malla. No se aplica una segunda conversión de unidades en Julia.

La salida `results/` contiene los VTK y `coefficients.toml` con CL, CD inviscido,
Cm, extremos de Cp y tiempo de resolución. Revisa normales, presiones y estela
antes de interpretar esos números. No es una predicción de resistencia total,
viscosidad o entrada en pérdida.

Por defecto se rechazan casos de más de 8,000 paneles para evitar lanzar sin
advertencia un sistema denso de gran tamaño. El límite es configurable mediante
un segundo argumento numérico, después de revisar la RAM disponible. Una sola
matriz densa de N×N en doble precisión ocupa aproximadamente 8N² bytes; el solver
necesita matrices y temporales adicionales.

## 4. Comparar tres resoluciones

Ya se ejecutaron `aircraft/coarse` y `aircraft/medium` con las mismas condiciones
(20 m/s, 4°, 1.225 kg/m³), geometría de origen y referencias.

| Magnitud | Gruesa (3410 paneles) | Media (7040 paneles) |
|---|---:|---:|
| CL | 0.150937 | 0.160208 |
| CD inviscido | 0.0109166 | 0.00884999 |
| Cm | -0.0187456 | -0.0256165 |
| Sustentación (N) | 266.25 | 282.61 |
| Fuerza lateral (N) | 2.54 | 0.96 |
| Cp mínimo | -7.463 | -12.229 |

Los cambios relativos respecto a la gruesa son 6.14 % en CL, 18.93 % en CD y
36.65 % en Cm (magnitudes de los cambios). No se ha demostrado convergencia.
El pico de Cp permanece cerca de `[2.41, 0.39, 0.01]` m y se intensifica al
refinar; su causa todavía no está determinada. Antes de aceptar las presiones
locales hay que revisar la geometría, los paneles y la estela en esa zona.
Todos los campos exportados son finitos y las fuerzas y momentos integrados
del VTK reproducen los coeficientes. La comprobación detallada está en
`exports/flowpanel/manta/aircraft/comparison_coarse_medium.json`.
Los resultados medios, incluidos VTK, estela y `pressure_cp.pos`, están bajo
`exports/flowpanel/manta/aircraft/medium/results/`.

Para repetir la comparación sin ejecutar otra simulación:

```powershell
& "C:\Users\PERSONAL\miniconda3\envs\wingcad\python.exe" analysis/flowpanel/compare.py exports/flowpanel/manta/aircraft --levels coarse medium
```

En PowerShell, prepara las otras mallas:

```powershell
& "C:\Users\PERSONAL\miniconda3\envs\wingcad\python.exe" analysis\flowpanel\prepare.py --mode wing --level medium
& "C:\Users\PERSONAL\miniconda3\envs\wingcad\python.exe" analysis\flowpanel\prepare.py --mode wing --level fine
```

Resuelve `medium` y `fine` con el mismo comando Julia, cambiando el último
directorio. Mantén las mismas condiciones de vuelo y referencias en los tres
`case.toml`. Después, en PowerShell:

```powershell
& "C:\Users\PERSONAL\miniconda3\envs\wingcad\python.exe" analysis\flowpanel\compare.py exports\flowpanel\manta\wing
```

El informe muestra coeficientes y cambios absolutos; no declara automáticamente
la convergencia. Los tamaños máximo/mínimo son 0.24/0.06 m, 0.16/0.04 m y
0.10/0.025 m. Debe revisarse el número real de paneles y que las diferencias
disminuyan. Ninguna malla se considera validada por llamarse `fine`.

## 5. Incorporar el cuerpo central

Tras revisar el ala, prepara el avión completo en PowerShell:

```powershell
& "C:\Users\PERSONAL\miniconda3\envs\wingcad\python.exe" analysis\flowpanel\prepare.py --mode aircraft --level all
```

Esta ruta **une copias del ala y del cuerpo central solo para análisis**. Se
exige un sólido válido y se malla su superficie exterior. No modifica el archivo
`.wingcad`, sus parámetros ni la exportación STEP multicuerpo de la aplicación.
No genera empalmes suaves. Si la unión falla o deja varios sólidos, se detiene.

Los casos quedan en `exports/flowpanel/manta/aircraft/`. Repite resolución e
informe de sensibilidad igual que con el ala. Las intersecciones ala-cuerpo y
el comienzo de la estela necesitan especial inspección.

Los scripts rechazan sobrescribir directorios de casos o resultados existentes.
Para nuevas iteraciones usa `--output exports/flowpanel/manta_run2` en la
preparación y pasa las rutas correspondientes a Julia y al comparador.
Los archivos bajo `exports/` ya están excluidos de Git.

## Referencias oficiales

- [FLOWPanel: instalación y plataformas](https://flow.byu.edu/FLOWPanel.jl/stable/)
- [Mallado CAD con Gmsh](https://flow.byu.edu/FLOWPanel.jl/stable/examples/blendedwingbody-gmsh/)
- [Bordes de salida](https://flow.byu.edu/FLOWPanel.jl/stable/examples/blendedwingbody-TE/)
- [Importación y solver](https://flow.byu.edu/FLOWPanel.jl/stable/examples/blendedwingbody-aero/)
- [Gmsh](https://gmsh.info/)
- [Julia](https://julialang.org/downloads/)
- [WSL en Windows](https://learn.microsoft.com/en-us/windows/wsl/install)
