# Exclusiones de antivirus para Fontis Remote

## El problema

Fontis Remote se basa en RustDesk. Los antivirus detectan **toda la familia
RustDesk** de forma heurística (nombres tipo `PUA:Win32/RustDesk`, `Riskware`,
`Remote Admin`) porque una herramienta de control remoto es, para el motor del
antivirus, indistinguible de un troyano de acceso remoto (RAT): captura
pantalla, inyecta teclado/ratón, corre como servicio, instala drivers.

**No es un fallo de la app.** El síntoma "instala pero no arranca" es el
bloqueador de comportamiento (HIPS) del antivirus terminando el proceso al
ejecutarse, o poniendo en cuarentena un DLL tras la instalación.

> ⚠️ Importante: una simple exclusión de análisis por ruta **no basta** para los
> antivirus con HIPS/bloqueo por comportamiento (Kaspersky, ESET, Norton). Hay
> que añadir la app como **aplicación de confianza** (desactivar la monitorización
> de comportamiento para ella), no solo excluirla del escaneo de archivos.

## Qué excluir (valores exactos del build 1.4.8-3)

| Tipo | Valor |
|---|---|
| Carpeta de instalación | `C:\Program Files\Fontis Remote\` (incluye subcarpetas `drivers\` y `usbmmidd_v2\`) |
| Proceso ejecutable | `Fontis Remote.exe` (sus procesos hijos `--server`, `--service`, `--tray` son el mismo .exe) |
| Servicio de Windows | `Fontis Remote` |
| Datos en ejecución | `%AppData%\Fontis Remote\` y `%ProgramData%\Fontis Remote\` (config y logs) |
| Drivers | `RustDeskPrinterDriver` (impresora), `usbmmidd` (pantalla virtual) |

## Cómo aplicarlo (flota en dominio AD / Intune)

El antivirus de tercero se gestiona desde **su propia consola central**, no
desde Intune/GPO (esas gestionan solo Microsoft Defender). Aplica la política a
todos los equipos desde:

### Kaspersky (Kaspersky Security Center)
1. Directiva → *Configuración avanzada de amenazas* → **Zona de confianza**.
2. *Aplicaciones de confianza* → Añadir → `Fontis Remote.exe` → marcar
   **"No analizar la actividad de la aplicación"** y "No analizar todo el
   tráfico". Esto es lo que evita el bloqueo por comportamiento.
3. *Exclusiones* → añadir la carpeta `C:\Program Files\Fontis Remote\`.

### ESET (ESET PROTECT)
1. Directiva → *Detection engine* → **Exclusiones de detección** y **Exclusiones
   de rendimiento**: añadir `C:\Program Files\Fontis Remote\`.
2. **HIPS** → regla que marque `Fontis Remote.exe` como proceso de confianza
   (permitir todas las operaciones). Sin esto, el HIPS mata el proceso al lanzar.

### Norton / Symantec y otros
- Añadir la carpeta a *Exclusiones / AutoProtect*.
- **Además** excluir del análisis de comportamiento (SONAR / Behavioral
  Protection) — es la capa que provoca el "no arranca".

## Fix duradero adicional

Reportar el falso positivo al fabricante del antivirus con el instalador Fontis
(subir el `.exe`/`.msi` a su portal de "false positive" / "whitelist"). Al
firmarse con reputación de fabricante, lo whitelistean. **Ojo:** el hash cambia
en cada release nuevo, así que la exclusión por carpeta/proceso (arriba) es la
protección estable; el reporte de hash es complementario.

## Nota sobre el build "ligero"

Se puede compilar una variante sin driver de impresora ni pantalla virtual
(menos superficie de detección). Solo ayuda si el bloqueo ocurre al registrar
esos drivers en el primer arranque; si el antivirus marca el núcleo
(`librustdesk.dll`), no cambia nada. La exclusión / app de confianza de arriba
es el fix principal en cualquier caso.
