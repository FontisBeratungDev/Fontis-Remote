# Fontis Remote

Fork de [RustDesk](https://github.com/rustdesk/rustdesk) **1.4.8** con la marca
Fontis y el servidor propio embebido. Este repositorio es autocontenido: incluye
la configuración de branding y el script que la aplica.

- Servidor embebido: `rustdesk.fontisberatung.ch` (bloqueado en ajustes del cliente)
- Configuración: [branding/branding.env](branding/branding.env)
- Script: `python scripts/apply_branding.py` (idempotente; re-ejecutar tras cambiar
  branding.env o los iconos, luego commitear)

## Generar instaladores

Push de un tag con formato `X.Y.Z-N` (por ejemplo `1.4.8-1`):

```
git tag 1.4.8-2
git push origin 1.4.8-2
```

El workflow **Flutter Tag Build** compila Windows (.exe/.msi), macOS (.dmg x64 y
arm64) y Linux (.deb/.rpm/AppImage/Flatpak) y publica todo en el Release del tag.
Alternativa manual: Actions → *Flutter Nightly Build* → Run workflow.

Requisito único del repo: **Settings → Actions → General → Workflow permissions →
"Read and write permissions"** (para que el CI pueda crear el Release).

Los jobs de Android/iOS/web pueden fallar sin claves de firma; no afectan a los
instaladores de escritorio. Los binarios van sin firma de código: Windows
SmartScreen y macOS Gatekeeper mostrarán aviso de editor desconocido.

## Cambios respecto a upstream

1. `libs/hbb_common/src/config.rs`: servidor, clave pública, nombre de app y
   `OVERWRITE_SETTINGS` (bloqueo de servidor). El submódulo `hbb_common` está
   **vendorizado** (carpeta normal) para mantener un solo repositorio.
2. Metadatos/nombre visible: `Runner.rc` (Windows), `Info.plist` (macOS),
   `res/*.desktop` (Linux).
3. Iconos y logo de cabecera (`flutter/assets/logo.png`, `res/*`, ICO/ICNS).
4. CI: cron nocturno y publicación F-Droid desactivados (solo builds manuales o
   por tag).

## Actualizar a una nueva versión de RustDesk

Clonar la nueva etiqueta upstream limpia, restaurar `branding/`, `scripts/` y
`FONTIS.md`, re-ejecutar el script (falla en voz alta si upstream cambió los
patrones esperados), re-aplicar los ajustes de CI del punto 4 y commitear.
El documento maestro con más detalle vive en el proyecto local
`f:\Proyectos\Fontis\Rustdesk\README.md`.
