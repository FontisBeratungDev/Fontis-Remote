# Bitácora — Fontis Remote

Cuaderno de trabajo del proyecto. Sirve para retomar el hilo desde cualquier equipo:
qué se hizo, cómo se hace cada proceso, qué está abierto y qué trampas ya nos mordieron.

**Regla de uso:** al terminar cada sesión de trabajo, añadir una entrada en
[Registro cronológico](#8-registro-cronológico) y actualizar [Pendientes](#6-pendientes)
e [Incidentes abiertos](#5-incidentes-abiertos). Commit + push junto con el resto de cambios.

**Este repo es PÚBLICO.** Aquí no van contraseñas, claves JWT, usuarios de SSH ni IPs.
Eso vive en el gestor de contraseñas del equipo y en el servidor.

---

## 1. Orientación rápida

| Qué | Dónde |
|---|---|
| Repo (fork de RustDesk con marca) | https://github.com/FontisBeratungDev/Fontis-Remote (remote `fontis`, rama `main`) |
| Base upstream actual | RustDesk **1.5.0** (`Cargo.toml`, desde 2026-10-11) |
| Release en distribución | flota en **`1.4.9-3`**; **`1.5.0-1`** publicado 2026-10-11 (piloto en el Mac de Basel antes de desplegar) |
| Configuración de marca | `branding/branding.env` (nombre, empresa, servidor, clave pública, API) |
| Script que aplica la marca | `scripts/apply_branding.py` (idempotente; falla en voz alta si upstream cambió un ancla) |
| Documentación del fork | `FONTIS.md` (cómo generar instaladores, cambios vs upstream, actualizar versión) |
| Kit de despliegue y guías de soporte | `deploy/` (ver §4) |
| Iconos y logos | `branding/icons/` (`icon-1024.png` definitivo, `social-preview.png`) |
| Servidor propio | `rustdesk.fontisberatung.ch` (hbbs/hbbr + rustdesk-api detrás de Apache con TLS wildcard) |
| CI | GitHub Actions del fork. Único disparador: push de tag `X.Y.Z-N` → workflow *Flutter Tag Build* |

### Retomar en otro equipo

```bash
git clone https://github.com/FontisBeratungDev/Fontis-Remote.git
cd Fontis-Remote
# Python 3 + Pillow para el script de marca (solo si se va a reaplicar o cambiar branding)
python scripts/apply_branding.py --help
```

No hace falta toolchain Rust/Flutter local: los instaladores los compila GitHub Actions.
Para el servidor hace falta la llave SSH del equipo (no está en el repo).

---

## 2. Historial de releases

| Tag | Fecha | Contenido | Estado |
|---|---|---|---|
| 1.4.8-1 | 2026-07-03 | Primer build con marca. Fallaron 2 jobs AppImage (`setuptools_scm` 10) | obsoleto |
| 1.4.8-2 | 2026-07-03 | Fix AppImage. 26 instaladores. Faltaban icon/logo in-app (`.gitignore *png`) | obsoleto |
| 1.4.8-3 | 2026-07-04 | Icono real, MSI "Fontis Remote", exe portable con metadatos, fix `.gitignore` | obsoleto |
| 1.4.8-4 | 2026-07-04 | Bundle macOS renombrado a `Fontis Remote.app` | obsoleto |
| 1.4.8-5 | 2026-07-05 | API server embebido, reintentos descarga engine en CI, fix rename instalador Windows, fix id interno Linux | obsoleto |
| 1.4.9-1 | 2026-08-14 | Rebase a upstream 1.4.9 (31 parches limpios) | obsoleto: muestra cartel falso "versión inferior" |
| 1.4.9-2 | 2026-08-14 | Desactivado check de actualización (`enable-check-update=N`), quitado job armv7-sciter | superado |
| **1.4.9-3** | 2026-08-28 | `input-source = Input source 2` por defecto (teclado en Abacus al cambiar de app) | **vigente** |
| 1.4.9-4 | 2026-10-11 | `focus_fix` macOS lado controlado: foco Java al volver desde otra app (Abacus). Opción `enable-macos-focus-fix` | build OK (21/24, 23 assets, ambos dmg; solo falla i686 no usado); por probar en el Mac de Basel |
| 1.5.0-1 | 2026-10-11 | Rebase a upstream 1.5.0 (WebRTC, whitelist de IDs, fixes macOS teclado). Todos los parches reaplicados; fixes CI: bits +x y MSI template | **build OK 25/26 (web skipped), 27 assets**; piloto pendiente |

Nota: "Acerca de" muestra `1.4.9` en los tres tags 1.4.9-N. El sufijo no llega al binario.
Para saber qué build tiene un usuario: menú teclado de la sesión → si "Input source 2" está
marcado por defecto es 1.4.9-3; si aparece el cartel "versión inferior" es 1.4.9-1.

---

## 3. Procesos (recetas)

### 3.1 Sacar un release

1. Cambios en código/branding → commit en `main`.
2. `git push fontis main` (nunca `--force` sobre `main`).
3. `git tag X.Y.Z-N && git push fontis X.Y.Z-N`.
4. Esperar el workflow *Flutter Tag Build* (~40-60 min). Publica el Release con los instaladores.
5. Verificar: Windows x64 exe+msi, macOS Intel+Apple Silicon dmg, Linux deb/rpm/AppImage/flatpak.

Si un job falla por descarga (engine de Flutter, xdotool 503, etc.) → *Re-run failed jobs*.
Si falla por código → **tag nuevo**; el re-run usa el commit del tag viejo.

### 3.2 Borrar y recrear un tag

```bash
git push fontis --delete X.Y.Z-N      # NO usar la sintaxis :refs/tags/...
git tag -d X.Y.Z-N
# borrar también el Release parcial en GitHub (Releases → Delete)
git tag X.Y.Z-N && git push fontis X.Y.Z-N
```

### 3.3 Actualizar a una nueva versión de RustDesk

Detalle en `FONTIS.md` → "Actualizar a una nueva versión". Resumen:

1. `git clone --branch <tag-upstream> --depth 1 https://github.com/rustdesk/rustdesk.git ../rustdesk-X.Y.Z`
2. `FONTIS_SRC=../rustdesk-X.Y.Z python -E -P scripts/apply_branding.py` → si falla, upstream movió un ancla: arreglar el parche. (`-E -P` y no `-I`: Pillow suele estar en el user-site, que `-I` ignora.)
3. Copiar overlay (`branding/`, `scripts/`, `deploy/`, `FONTIS.md`, `BITACORA.md`) al clon; vendorizar `libs/hbb_common` (quitar el submódulo).
4. El clon es shallow: llevar el árbol a `main` con `robocopy <clon> <fork> /MIR /XD .git /XF .git` **desde PowerShell** (en Git Bash `/MIR` se convierte en ruta) o `rsync -a --delete --exclude .git`, y commit normal (fast-forward). Antes: copiar overlay al clon y borrar `.gitmodules` + `libs/hbb_common/.git`.
5. **Restaurar bits de ejecución** (robocopy/Windows los pierde en scripts nuevos): comparar
   `git -C <clon> ls-files -s | awk '$1=="100755"'` con el fork y aplicar `git update-index --chmod=+x <archivo>`.
   Síntoma si se olvida: AppImage falla con `Permission denied` / exit 126.
6. Push `main` + tag `X.Y.Z-1`.

### 3.4 Leer logs de CI sin `gh`

Los logs anónimos dan 403 aunque el repo sea público. Usar el token de push:

```bash
TOKEN=$(printf "protocol=https\nhost=github.com\n" | git credential fill | sed -n 's/^password=//p')
curl -sH "Authorization: Bearer $TOKEN" \
  https://api.github.com/repos/FontisBeratungDev/Fontis-Remote/actions/runs?per_page=5
```

### 3.5 Verificar un MSI sin instalarlo

```powershell
msiexec /a Fontis-Remote.msi /qn TARGETDIR=C:\tmp\msi
```

Buscar servidor y clave en `librustdesk.dll`. Ojo: el compilador parte cadenas cortas
("Fontis R"+"emote"); un falso negativo buscando el texto contiguo no es un bug.

### 3.6 Servidor

- Docker Compose en el VPS (`/home/rustdesk`): `hbbs`, `hbbr` con imagen **oficial `rustdesk/rustdesk-server:1.1.16`** (desde 2026-08-27; antes lejianwen/rustdesk-server) y `rustdesk-api` (`lejianwen/rustdesk-api:latest` = v2.7) en `127.0.0.1:21114`. Las variables `RUSTDESK_API_*` siguen en hbbs/hbbr pero la imagen oficial no las usa.
- Apache publica `https://rustdesk.fontisberatung.ch` → api/consola `/_admin/`, `wss` en `/ws/id` y `/ws/relay`. Cert wildcard Sectigo hasta dic-2026.
- Puertos abiertos: 21115-21119 TCP (21116 UDP sin verificar desde fuera).
- Plantillas y guía en `deploy/docker-compose.yml`, `deploy/nginx-rustdesk.conf`, `deploy/README.md`.
- Backups del compose en el servidor: `.bak` (pre-api), `.bak-lejianwen` (pre-migración a lejianwen) y `.bak-20260827` (config lejianwen, rollback si vuelve el error de login).
- Historia: 2026-08-14 se pasó a lejianwen/rustdesk-server porque con sesión iniciada el cliente fallaba ("Failed to secure tcp: deadline has elapsed"). 2026-08-27 se volvió a la oficial 1.1.16 (motivo no registrado; 1.1.16 corrige amplificación UDP en punch-hole y lejianwen no publica desde 2025-09). Verificar que el login no ha vuelto a romper las conexiones.

---

## 4. Guías de soporte (en `deploy/`)

| Tema | Archivo | Resumen |
|---|---|---|
| Antivirus de terceros mata la app | `antivirus-exclusiones.md` | Añadir como app de confianza en la consola del AV (exclusión de ruta no basta con HIPS) |
| Acceso desatendido (login con pantalla bloqueada, auto-login, no suspender) | `acceso-desatendido.md`, `windows-desatendido.ps1`, `macos-desatendido.sh`, `linux-desatendido.sh` | Config del SO, no del fork. BitLocker convive; FileVault/LUKS rompen el auto-login |
| Wake-on-LAN | `wake-on-lan.md`, `wol-windows.ps1`, `wol-macos.sh` | Ya existe en RustDesk; necesita otro equipo encendido en la misma LAN |
| Servicio persistente | `servicio-persistente.md` | — |
| macOS Gatekeeper "dañado" | `FONTIS.md` | Falta notarización: `xattr -cr "/Applications/Fontis Remote.app"` |
| **Instalar o actualizar en macOS** (builds sin firma Apple) | — | 1) Cerrar Fontis Remote y sustituir la app en Aplicaciones. 2) `xattr -cr "/Applications/Fontis Remote.app"`. 3) En Privacidad y seguridad, **quitar con − y volver a añadir** Fontis Remote en Accesibilidad, Grabación de pantalla y Monitorización de entrada: cada build nueva invalida los permisos aunque sigan marcados. 4) Reiniciar. Sin esto la app no arranca o no acepta conexiones (visto con 1.5.0-1 en Basel, 2026-10-12). Se acaba con firma Developer ID + notarización. |

Funciones "tipo RealVNC" pedidas y que **ya existen** en RustDesk (no requieren build):
audio remoto (default on), micrófono (Voice Call), WoL, login en pantalla bloqueada.
Antes de "crear" una función, buscarla en el código.

---

## 5. Incidentes abiertos

### 5.1 Abacus en Mac remoto pierde el teclado al cambiar de ventana (abierto 2026-10-11)

**Reporte (contable):** en el PC de Basel (Mac), en Abacus (asientos y Kreditoren), al pasar a
otro archivo y volver, el módulo queda bloqueado. Minimizar la ventana lo reactiva.
Ya se aplicaron Input source 2 y 1.4.9-3: persiste.

**Diagnóstico:** Abacus corre como ULC (Java Swing en el Mac, lanzado por AbaClient con su
OpenJDK). Bug conocido de Java en macOS con eventos de entrada sintéticos:
[JDK-8185326](https://bugs.openjdk.org/browse/JDK-8185326) (reproducible con VNC y Screen
Sharing de Apple, nunca arreglado). Mismo patrón en
[rustdesk #13897](https://github.com/rustdesk/rustdesk/discussions/13897). No es bug del fork.

**Workaround inmediato:** al volver a Abacus, clicar el icono de AbaClient en el **Dock**, no la ventana.

**Resultados de las pruebas (2026-10-11):**
- [x] Clic en el Dock: NO devuelve el teclado (a diferencia del reporte JDK). Solo minimizar/restaurar funciona.
- [x] Sentada físicamente en el Mac de Basel: NO falla. Solo remoto.
- [x] Desde otro Mac con Screen Sharing de Apple: falla IGUAL. Confirmado: bug de Java con entrada sintética, no del cliente Fontis Remote.
- [ ] Versión de AbaClient y macOS en Basel: desconocida (AbaClient → menú "Über AbaClient"; actual 4.3.1194).
- [x] El "otro archivo" son otros programas (cambio de app, no ventanas de Abacus).

**Lectura:** minimizar/restaurar fuerza `makeKeyAndOrderFront` → la ventana Java vuelve a ser
key window y Swing recupera el foco. Activar la app (Dock) no basta porque la app ya está activa.

**Prueba de validación de la mitigación (sin build), en Terminal del Mac de Basel con el módulo bloqueado:**

```bash
# 1. nombre del proceso de Abacus (buscar AbaClient / java / Abacus en la lista)
osascript -e 'tell application "System Events" to get name of every process whose background only is false'
# 2. variante A: re-key de la ventana vía Accessibility
osascript -e 'tell application "System Events" to tell process "AbaClient" to perform action "AXRaise" of window 1'
# 3. variante B (equivale a minimizar/restaurar):
osascript -e 'tell application "System Events" to tell process "AbaClient" to set value of attribute "AXMinimized" of window 1 to true'          -e 'delay 0.3'          -e 'tell application "System Events" to tell process "AbaClient" to set value of attribute "AXMinimized" of window 1 to false'
```

Terminal pedirá permiso de Accesibilidad la primera vez. Si A o B devuelven el teclado, la
mitigación en el fork (lado controlado, misma llamada AX tras cada clic que cambia de ventana) es viable.

**Hallazgo clave (2026-10-11):** Abacus NO corre en Basel. Está hospedado por **STARTNOW.SUPPORT AG**
(Abacus Gold Partner, hosting en la nube). Pie de AbaMenu en el Mac de Basel:
`V 2026.202 | Hosting by STARTNOW.SUPPORT AG | Release 15.02.2026 - Patch 15.09.2026`.
El Mac de Basel es solo un cliente (proceso `AbaClientLauncher`) que se conecta al hosting por internet.

**Opciones de fondo:**
1. ~~AbaClient en el Mac de la contable~~ **DESCARTADA (2026-10-11): política de empresa, solo se trabaja desde los equipos remotos.** Conectado directamente al hosting de
   STARTNOW.SUPPORT con su mismo usuario. Sin escritorio remoto → sin bug de foco Java, y más rápido.
   Pasos: descargar AbaClient macOS 4.3.1194 (exige macOS 14+) de downloads.abacus.ch; copiar la URL/abalink
   de conexión desde el AbaClientLauncher del Mac de Basel (o pedirla a STARTNOW.SUPPORT); iniciar sesión.
   Confirmar con el hosting que no hay restricción por IP/dispositivo/certificado para un equipo nuevo.
2. **IMPLEMENTADA (2026-10-11, sin build aún):** `patch_macos_java_focus` en `apply_branding.py` → módulo `focus_fix` en `src/platform/macos.rs` + hooks en `input_service.rs`. En cada clic izquierdo que cae en una ventana (layer 0) de una app que NO es la frontal: 120 ms tras el mouse-up, `NSRunningApplication.activateWithOptions` + `AXRaise` de la ventana bajo el cursor (lo mismo que las pruebas A y C). Si la ventana ya no está bajo el cursor (cerrada/minimizada) no hace nada. Desactivable: opción del servidor `enable-macos-focus-fix = "N"`. Validación local imposible (sin toolchain Rust ni Mac): compila en CI macOS, se prueba instalando 1.4.9-4 solo en el Mac de Basel. Diseño original: en cada clic sintético, activar la app/ventana bajo el cursor (`NSRunningApplication.activateWithOptions` o Accessibility `kAXRaiseAction`), emulando el clic del Dock. Opcional y desactivable. No testeable sin Mac; iría en 1.4.9-4.
3. Consultar a Abacus Support si hay flag de Java para ULC.

---

## 6. Pendientes

- [ ] **Firma de código Windows** (Sectigo OV/EV). Aplazada por decisión de Fontis (2026-07-04). Sin ella SmartScreen avisa. Azure Trusted Signing no disponible para Suiza.
- [ ] **Notarización Apple**. Misma decisión.
- [ ] **Desplegar 1.4.9-3** en toda la flota (quita el cartel falso de versión y trae Input source 2).
- [ ] **Borrar releases obsoletos** (1.4.8-*, 1.4.9-1, 1.4.9-2) cuando la flota esté en 1.4.9-3.
- [ ] **Avatar de la organización y social preview** en GitHub (manual, Settings de la org): `branding/icons/icon-1024.png`, `branding/icons/social-preview.png`.
- [ ] Renombrar nombres de archivo de los instaladores (siguen `rustdesk-X.Y.Z-*`) y paquetes Linux.
- [ ] README del fork 100 % propio.
- [ ] Build ligero sin drivers (printer/virtual display). Solo si un AV bloquea en el registro del driver.
- [ ] Verificar 21116/UDP desde fuera.
- [ ] Incidente 5.1.
- [ ] macOS: rutas `Fontis Remote` sin comillas en `daemon.plist` e `install/update/uninstall.scpt` (servicio root nunca arranca; afecta acceso desatendido antes del login). Arreglo previsto en 1.5.0-2, con `allow-auto-update=N` forzado.
- [ ] Servidor: confirmar con un cliente **con sesión iniciada** que conecta a un equipo con hbbs oficial 1.1.16 (si vuelve "Failed to secure tcp", rollback a `.bak-20260827`).
- [ ] Servidor: `rustdesk-api` v2.7 sin releases desde 2025-09. Probar login y libreta de direcciones con el cliente 1.5.0-1.
- [x] Servidor: Docker actualizado 2026-10-11 (29.8.2 → 29.9.0, containerd 2.4.1). 17 contenedores sanos tras el reinicio.
- [ ] Servidor: 12 metapaquetes PHP retenidos a propósito (`apt-mark hold`): instalarlos pasaría Apache/Nextcloud de PHP 8.1 a 8.4. Decisión aparte, con prueba de Nextcloud.
- [ ] Servidor: `php8.2-fpm` y `php8.3-fpm` usan librerías antiguas (needrestart); reiniciarlos en una ventana tranquila.
- [ ] Revisión automática del commit 1.5.0 marcó posible agotamiento de recursos en `src/client/io_loop.rs` (upstream: `mpsc::unbounded_channel` en la cola de reconexión, +675 líneas). Archivo idéntico a upstream, sin parches nuestros. Vigilar issues upstream; no bloquea.

---

## 7. Lecciones y trampas

- `.gitignore` de RustDesk tiene `*png`: cualquier PNG nuevo queda fuera del commit en silencio. `apply_branding.py` añade las excepciones; si se añade otro PNG, añadir excepción.
- El clon de upstream es shallow: GitHub rechaza pushes shallow y no se pueden hacer fetch de objetos. Por eso `main` del fork es un commit raíz propio y las actualizaciones van por copia de árbol.
- Nunca `git push --force` sobre `main`. Nunca pushear un tag sobre historia desconectada.
- Los *Re-run failed jobs* no sirven para fixes de código: usan el commit del tag.
- Casi todos los fallos de CI son descargas transitorias (engine Flutter, xdotool, flatpak), no la marca. Si fuera la marca fallarían los 22 jobs.
- `armv7-sciter` (UI legacy ARM 32-bit) está quitado de la matriz: no se usa.
- Renombrar el bundle macOS toca 6 sitios: `AppInfo.xcconfig`, `project.pbxproj`, `Runner.xcscheme`, `flutter-build.yml` (×2) y `build.py`.
- En Linux el id interno sigue siendo `rustdesk` (unit systemd, proceso, .desktop); solo el nombre visible es "Fontis Remote". Un id con espacio rompía systemctl y tray.
- El instalador GUI de Windows (`install_me`) no renombraba el exe; parcheado. El MSI ya lo hacía.
- `/api/version` del rustdesk-api devuelve la versión del api, no del cliente: por eso el cartel falso de "versión inferior". Check de actualización desactivado en el cliente.
- La opción `input-source` es local al equipo que controla y aplica en Windows y macOS (no solo macOS). Guardar un valor igual al default lo borra de la config.
- Ver el código antes de "crear" una función: audio, micro, WoL y login en pantalla bloqueada ya existían.
- Job `i686-pc-windows-msvc` (sciter 32-bit, no usado por la flota) falla desde 2026-10 en "Install Rust toolchain": rustup nuevo exige `--force-non-host`. Backport upstream como `patch_ci_sciter_toolchain`. El resto de jobs y el Release no dependen de él (solo `publish_unsigned`, que no se usa).

---

## 8. Registro cronológico

Entradas resumidas. Las nuevas se añaden al final.

- **2026-07-03** — Decisión: fork del código fuente (no generador Pro). Repo creado, overlay (`branding/`, `scripts/`, `FONTIS.md`) dentro del fork. Datos reales del servidor aplicados. CI ajustada (solo tag build; `permissions: contents: write`). Tags 1.4.8-1 y 1.4.8-2.
- **2026-07-04** — Icono definitivo. Branding de empaquetado Windows (MSI, exe portable). Fix `.gitignore *png`. Tag 1.4.8-3 (release de distribución). README del fork brandeado. Bundle macOS renombrado (tag 1.4.8-4). Fase 2 iniciada: rustdesk-api desplegado en el VPS detrás de Apache con TLS wildcard; consola `/_admin/`. Firma de código: Suiza excluida de Azure Trusted Signing; compra aplazada. Guías: antivirus, acceso desatendido (Win/mac/Linux), audio/mic (ya existían).
- **2026-07-05** — API server embebido en el cliente. Reintentos de descarga del engine en CI. Fix rename exe en instalador GUI Windows. Fix id interno Linux. WoL documentado. Tag 1.4.8-5.
- **2026-07/08** — Bug "Failed to secure tcp" con sesión iniciada: hbbs OSS no valida el token del api. Migrados hbbs/hbbr a lejianwen/rustdesk-server con JWT compartido. Confirmado resuelto 2026-08-14.
- **2026-08-14** — Rebase a RustDesk 1.4.9 (31 parches limpios). Tag 1.4.9-1. Cartel falso "versión inferior" → check de actualización desactivado; job armv7-sciter quitado. Tag 1.4.9-2.
- **2026-08-28** — Abacus en Mac: tras cambiar de app no deja escribir. Causa: Input source 1 (hook de teclado en el equipo que controla). Default cambiado a Input source 2. Tag 1.4.9-3.
- **2026-10-11 (tarde)** — Pruebas osascript en el Mac de Basel: `set frontmost` y `AXRaise` devuelven el teclado; minimizar por script no. Política de empresa: solo equipos remotos (AbaClient local descartado). Implementado `focus_fix` (parche `patch_macos_java_focus`), docs en FONTIS.md. Tag 1.4.9-4 empujado (commit 8df3565, run 38159177559). Job i686 falló por rustup (`--force-non-host`); backport aplicado en el árbol, pendiente de commit para el siguiente tag.
- **2026-10-11** — Revisión de pendientes. Contable reporta el mismo síntoma con 1.4.9-3 e Input source 2, remoto = Mac. Diagnóstico: bug de Java/ULC en macOS con entrada sintética (JDK-8185326). Workaround Dock; pruebas y opciones en §5.1. Creada esta bitácora.

**Nota prueba osascript:** `process "AbaClientLauncher"` dio error -1728 (no existe) con Abacus abierto: el launcher arranca otro proceso (contenedor AbaClient / java). Usar la variante con `delay` + proceso frontmost en vez de nombre fijo.
**Datos del Mac de Basel (2026-10-11, pruebas osascript):** proceso de Abacus = `java` (JRE 21 en
`/Applications/AbaClientManager.app/Contents/Plugins/Java.Runtime/.../jre21/bin/java`), nombre visible "Abacus".
Todas las ventanas (AbaMenu y módulos como "21 Zahlungen erfassen/korrigieren – Glambou Retail AG [50101]")
cuelgan del mismo proceso. `AXRaise` y `set frontmost` ejecutan sin error. `AXMinimized` true/false con
delay 0.3 s NO devolvió el teclado (posible: animación interrumpida; repetir con delay 2 s). Resultado de
AXRaise y frontmost sobre el módulo bloqueado: pendiente de confirmación explícita.
- **2026-10-11 (noche)** — Actualización a RustDesk 1.5.0: clon shallow `rustdesk-1.5.0`, 31+ parches reaplicados limpios (upstream ya trae `--force-non-host`), iconos regenerados, overlay copiado, hbb_common vendorizado, robocopy /MIR. Script: helper `rel()` para rutas fuera del proyecto. Commit y tag `1.5.0-1`.
- **2026-10-11 (noche, 2)** — Build 1.5.0-1: fallan AppImage (bits +x perdidos en `appimage/build-apprun.sh` y 3 scripts más) y Windows x64 (paso nuevo upstream "Build pre-built MSI template" espera `rustdesk.exe`, ya renombrado a `Fontis Remote.exe`). Fix: `git update-index --chmod=+x` + parche del `mv` del template en `patch_windows_packaging`. Re-tag 1.5.0-1.
- **2026-10-11 (noche, 3)** — Revisión del servidor: hbbs/hbbr oficial 1.1.16 (= última) y rustdesk-api v2.7 (= última), digests iguales a Docker Hub: sin actualizaciones de RustDesk. Descubierto que desde 2026-08-27 ya no se usa lejianwen/rustdesk-server; bitácora corregida. Contenedores reiniciados 2026-10-02 (reinicio del host).
- **2026-10-11 (noche, 4)** — Servidor: actualizados los 6 paquetes Docker; PHP retenido sin tocar. Comprobado: 17 contenedores healthy, puertos 21114-21119 y 21116/udp escuchando, rustdesk api/_admin y Nextcloud 200. El host comparte Docker con otros servicios: actualizar Docker los reinicia todos (~5 s; algunos tardan ~5 min en estar healthy).
- **2026-10-11 (noche, 5)** — Build 1.5.0-1 (re-tag sobre 9a1e90f) verde: 25/26 jobs, 27 assets (Windows x64/ARM64 exe+msi, macOS Intel+Apple Silicon, Linux deb/rpm/AppImage/flatpak). Clon temporal borrado.
- **2026-10-12** — 1.5.0-1 instalado en el Mac de Basel: no arrancaba; causa = firma/permisos de build sin certificado. Resuelto con el procedimiento de §4. Detectados además fallos latentes desde 1.4.8-4: rutas con espacio sin comillas en los scripts del servicio macOS (`daemon.plist` con `/bin/sh -c`, `install/update/uninstall.scpt`) → el servicio root no arranca. Propuesto 1.5.0-2 con el arreglo. Pendiente: prueba de Abacus con la contable sobre 1.5.0-1.
