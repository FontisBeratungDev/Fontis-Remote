#!/usr/bin/env python3
"""Aplica el branding de Fontis sobre el árbol de código de RustDesk.

Lee branding/branding.env y parchea el código clonado en ./rustdesk:
  - Servidor ID/Rendezvous y clave pública embebidos (config.rs)
  - Nombre visible de la aplicación (config.rs, Runner.rc, Info.plist, .desktop)
  - Bloqueo opcional del servidor en ajustes (OVERWRITE_SETTINGS)
  - Iconos y logo de cabecera (requiere Pillow para generar tamaños)

El script es idempotente: se puede ejecutar tantas veces como se quiera.
Falla en voz alta si un patrón esperado no aparece exactamente una vez
(señal de que la versión upstream cambió y hay que revisar el parche).

Uso:
    python scripts/apply_branding.py [--allow-placeholders] [--skip-icons]
"""

import argparse
import re
import sys
from pathlib import Path

import os

PROJECT_ROOT = Path(__file__).resolve().parent.parent
# Override opcional del árbol de código (para actualizar a una versión nueva
# en un directorio aparte): FONTIS_SRC=/ruta/al/clon
# Dos disposiciones por defecto: proyecto local (fuente en ./rustdesk) o
# ejecución dentro del propio fork (fuente en la raíz del repo).
if os.environ.get("FONTIS_SRC"):
    SRC = Path(os.environ["FONTIS_SRC"]).resolve()
else:
    SRC = PROJECT_ROOT / "rustdesk"
    if not SRC.exists() and (PROJECT_ROOT / "libs" / "hbb_common").exists():
        SRC = PROJECT_ROOT
BRANDING_DIR = PROJECT_ROOT / "branding"
ENV_FILE = BRANDING_DIR / "branding.env"
ICONS_DIR = BRANDING_DIR / "icons"

CONFIG_RS = SRC / "libs" / "hbb_common" / "src" / "config.rs"
RUNNER_RC = SRC / "flutter" / "windows" / "runner" / "Runner.rc"
INFO_PLIST = SRC / "flutter" / "macos" / "Runner" / "Info.plist"
DESKTOP_FILES = [SRC / "res" / "rustdesk.desktop", SRC / "res" / "rustdesk-link.desktop"]
PORTABLE_TOML = SRC / "libs" / "portable" / "Cargo.toml"
MSI_PREPROCESS = SRC / "res" / "msi" / "preprocess.py"
FLUTTER_BUILD_YML = SRC / ".github" / "workflows" / "flutter-build.yml"
WINDOWS_RS = SRC / "src" / "platform" / "windows.rs"
LINUX_RS = SRC / "src" / "platform" / "linux.rs"
LINUX_SERVICE = SRC / "res" / "rustdesk.service"
MACOS_XCCONFIG = SRC / "flutter" / "macos" / "Runner" / "Configs" / "AppInfo.xcconfig"
BUILD_PY = SRC / "build.py"
MACOS_PBXPROJ = SRC / "flutter" / "macos" / "Runner.xcodeproj" / "project.pbxproj"
MACOS_XCSCHEME = (
    SRC / "flutter" / "macos" / "Runner.xcodeproj" / "xcshareddata"
    / "xcschemes" / "Runner.xcscheme"
)

applied = []
warnings = []


def fail(msg: str) -> None:
    print(f"\n[ERROR] {msg}", file=sys.stderr)
    sys.exit(1)


def load_env(path: Path) -> dict:
    if not path.exists():
        fail(f"No existe {path}")
    env = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip()
    return env


def patch(path: Path, pattern: str, replacement: str, desc: str, count: int = 1,
          flags: int = 0) -> None:
    """Reemplaza `pattern` por `replacement`; exige exactamente `count` coincidencias.

    count=0 significa "todas las que haya, mínimo una".
    """
    if not path.exists():
        fail(f"{desc}: no existe {path}")
    text = path.read_text(encoding="utf-8")
    new_text, n = re.subn(pattern, replacement, text, flags=flags)
    expected = "≥1" if count == 0 else str(count)
    if (count == 0 and n < 1) or (count > 0 and n != count):
        fail(
            f"{desc}: se esperaban {expected} coincidencias y hubo {n} en {path}.\n"
            f"  Patrón: {pattern}\n"
            f"  Es probable que la versión upstream haya cambiado; revisa el parche."
        )
    if new_text != text:
        path.write_text(new_text, encoding="utf-8")
        applied.append(f"{desc}  ->  {path.relative_to(PROJECT_ROOT)}")
    else:
        applied.append(f"{desc}  (ya aplicado)")


def rust_str(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


# ----------------------------------------------------------------------------
# Parches de código
# ----------------------------------------------------------------------------

def patch_server(env: dict) -> None:
    host = env["RENDEZVOUS_SERVER"]
    key = env["RS_PUB_KEY"]
    patch(
        CONFIG_RS,
        r'pub const RENDEZVOUS_SERVERS: &\[&str\] = &\[[^\]]*\];',
        f'pub const RENDEZVOUS_SERVERS: &[&str] = &["{rust_str(host)}"];',
        "Servidor rendezvous embebido",
    )
    patch(
        CONFIG_RS,
        r'pub const RS_PUB_KEY: &str = "[^"]*";',
        f'pub const RS_PUB_KEY: &str = "{rust_str(key)}";',
        "Clave pública embebida",
    )


def patch_app_name(env: dict) -> None:
    app_name = env["APP_NAME"]
    patch(
        CONFIG_RS,
        r'pub static ref APP_NAME: RwLock<String> = RwLock::new\("[^"]*"\.to_owned\(\)\);',
        f'pub static ref APP_NAME: RwLock<String> = RwLock::new("{rust_str(app_name)}".to_owned());',
        "Nombre de aplicación (núcleo)",
    )

    # Metadatos del ejecutable de Windows
    company = env.get("COMPANY", app_name)
    patch(RUNNER_RC, r'(VALUE "CompanyName", )"[^"]*"',
          rf'\1"{company}"', "Metadatos exe Windows: CompanyName")
    patch(RUNNER_RC, r'(VALUE "FileDescription", )"[^"]*"',
          rf'\1"{app_name}"', "Metadatos exe Windows: FileDescription")
    patch(RUNNER_RC, r'(VALUE "ProductName", )"[^"]*"',
          rf'\1"{app_name}"', "Metadatos exe Windows: ProductName")

    # Nombre visible en macOS (sin renombrar el bundle, que rompería el CI)
    plist_text = INFO_PLIST.read_text(encoding="utf-8")
    if "CFBundleDisplayName" in plist_text:
        patch(
            INFO_PLIST,
            r'(<key>CFBundleDisplayName</key>\s*<string>)[^<]*(</string>)',
            rf'\g<1>{app_name}\g<2>',
            "Nombre visible macOS (CFBundleDisplayName)",
        )
    else:
        patch(
            INFO_PLIST,
            r'(\t<key>CFBundleName</key>)',
            f'\t<key>CFBundleDisplayName</key>\n\t<string>{app_name}</string>\n\\1',
            "Nombre visible macOS (CFBundleDisplayName)",
        )

    # Entradas de menú en Linux
    for desktop in DESKTOP_FILES:
        patch(desktop, r'^Name=.*$', f'Name={app_name}',
              f"Nombre visible Linux ({desktop.name})", count=0, flags=re.MULTILINE)


GITIGNORE_BLOCK = """
# Fontis: el `*png` de arriba ignora cualquier PNG nuevo; los assets de
# marca deben versionarse para que el fork sea autocontenido y los builds
# de CI incluyan el logo/icono dentro de la app.
!branding/icons/*.png
!flutter/assets/icon.png
!flutter/assets/logo.png
!flutter/assets/logo_light.png
!flutter/assets/logo_dark.png
"""


def patch_gitignore(env: dict) -> None:
    gitignore = SRC / ".gitignore"
    text = gitignore.read_text(encoding="utf-8")
    if "!branding/icons/*.png" in text:
        applied.append(".gitignore: excepciones de assets  (ya aplicado)")
        return
    gitignore.write_text(text.rstrip("\n") + "\n" + GITIGNORE_BLOCK, encoding="utf-8")
    applied.append(".gitignore: excepciones para assets de marca (el *png los ignoraba)")


def patch_readme_header(env: dict) -> None:
    """Cabecera del README del fork: logo Fontis en lugar del de RustDesk."""
    app_name = env["APP_NAME"]
    logo_name = env.get("LOGO_FILE", "logo_fontis_primary.png")
    patch(
        SRC / "README.md",
        r'<img src="[^"]*" alt="(?:RustDesk - Your remote desktop|' + re.escape(app_name) + r')">',
        f'<img src="branding/icons/{logo_name}" alt="{app_name}">',
        "README del fork: logo de cabecera",
    )


def patch_readme_urls(env: dict) -> None:
    """URLs del README que apuntan a rustdesk/rustdesk -> repo del fork.

    Se conservan a propósito: la wiki (el fork no tiene), los vídeos de
    `assets/` (URLs globales de GitHub) y los repos del servidor
    (rustdesk-server, rustdesk-server-demo).
    """
    repo = env.get("REPO_URL", "").rstrip("/")
    if not repo:
        warnings.append("Sin REPO_URL en branding.env: URLs del README no cambiadas.")
        return
    readme = SRC / "README.md"
    text = readme.read_text(encoding="utf-8")
    total = 0
    for pattern, replacement in [
        (r'https://github\.com/rustdesk/rustdesk/tree/master/', f'{repo}/tree/main/'),
        (r'https://github\.com/rustdesk/rustdesk/blob/master/', f'{repo}/blob/main/'),
        (r'https://github\.com/rustdesk/rustdesk/releases/tag/nightly', f'{repo}/releases'),
        (r'https://github\.com/rustdesk/rustdesk/releases(?![\w/-])', f'{repo}/releases'),
        (r'https://github\.com/rustdesk/rustdesk(?![\w/-])', repo),
    ]:
        text, n = re.subn(pattern, replacement, text)
        total += n
    if total:
        readme.write_text(text, encoding="utf-8")
        applied.append(f"README del fork: {total} URLs -> repo Fontis")
    else:
        applied.append("README del fork: URLs  (ya aplicado)")


def patch_readme_cleanup(env: dict) -> None:
    """Quita del README del fork secciones de la comunidad RustDesk:
    índice de traducciones, "Chat with us" y badges de F-Droid/Flathub."""
    readme = SRC / "README.md"
    text = readme.read_text(encoding="utf-8")
    total = 0
    for pattern in [
        # Índice de traducciones dentro de la cabecera
        r'^\s*\[<a href="docs/README-[A-Z]{2,4}\.md">.*<br>\n',
        # Petición de ayuda con traducciones
        r'^\s*<b>We need your help to translate.*</b>\n',
        # Línea de redes sociales
        r'^Chat with us: .*\n+',
        # Badges de tiendas (F-Droid / Flathub)
        r'\[<img src="https://f-droid\.org/[^\]]*\]\([^)]*\)\n?',
        r'\[<img src="https://flathub\.org/[^\]]*\]\([^)]*\)\n?',
    ]:
        text, n = re.subn(pattern, "", text, flags=re.MULTILINE)
        total += n
    if total:
        readme.write_text(text, encoding="utf-8")
        applied.append(f"README del fork: {total} secciones de comunidad eliminadas")
    else:
        applied.append("README del fork: limpieza de secciones  (ya aplicado)")


def patch_windows_packaging(env: dict) -> None:
    """Empaquetado Windows: exe portable exterior y paquete MSI."""
    app_name = env["APP_NAME"]
    company = env.get("COMPANY", app_name)
    copyright_line = f"Copyright © {company}. All rights reserved."

    # Metadatos del empaquetador portable (el .exe autoextraíble que se descarga)
    patch(PORTABLE_TOML, r'(^description = )"[^"]*"',
          rf'\1"{app_name}"', "Portable: description", flags=re.MULTILINE)
    patch(PORTABLE_TOML, r'(^ProductName = )"[^"]*"',
          rf'\1"{app_name}"', "Portable: ProductName", flags=re.MULTILINE)
    patch(PORTABLE_TOML, r'(^FileDescription = )"[^"]*"',
          rf'\1"{app_name}"', "Portable: FileDescription", flags=re.MULTILINE)
    patch(PORTABLE_TOML, r'(^LegalCopyright = )"[^"]*"',
          rf'\1"{copyright_line}"', "Portable: LegalCopyright", flags=re.MULTILINE)

    # Copyright del ejecutable interior (Runner.rc)
    patch(RUNNER_RC, r'(VALUE "LegalCopyright", )"[^"]*"',
          rf'\1"{copyright_line}"', "Metadatos exe Windows: LegalCopyright")

    # preprocess.py ejecuta el exe sin comillas; con nombre con espacio se rompe
    patch(
        MSI_PREPROCESS,
        r'f"\{dist_app\} \{args\}"|f\'"\{dist_app\}" \{args\}\'',
        "f'\"{dist_app}\" {args}'",
        "MSI: rutas con espacios en preprocess.py",
    )

    # El job de Windows genera el MSI con el nombre y fabricante de la marca.
    # El MSI exige que el exe del dist se llame <app_name>.exe, así que se
    # renombra justo antes (el exe portable ya se empaquetó en un paso anterior).
    patch(
        FLUTTER_BUILD_YML,
        r'(?:          Move-Item [^\n]*\n)?          python preprocess\.py --arp -d \.\./\.\./rustdesk[^\n]*',
        f'          Move-Item ../../rustdesk/rustdesk.exe "../../rustdesk/{app_name}.exe"\n'
        f'          python preprocess.py --arp -d ../../rustdesk --app-name "{app_name}" -m "{company}"',
        "MSI: nombre de producto y fabricante en el CI",
    )


def patch_service_recovery(env: dict) -> None:
    """Auto-reinicio del servicio Linux ante fallo (Restart=always).

    El servicio ya arranca en el boot (WantedBy=multi-user) y persiste aunque se
    cierre la GUI. Se añade recuperación ante crash. macOS ya tiene KeepAlive;
    Windows se cubre por el script de despliegue (sc failure).
    """
    if "Restart=always" in LINUX_SERVICE.read_text(encoding="utf-8"):
        applied.append("Linux: Restart=always en el servicio  (ya aplicado)")
        return
    patch(
        LINUX_SERVICE,
        r'TimeoutStopSec=30\n',
        "TimeoutStopSec=30\nRestart=always\nRestartSec=2\n",
        "Linux: Restart=always en rustdesk.service",
    )


def patch_linux_app_id(env: dict) -> None:
    """Linux: usa 'rustdesk' como identificador interno en vez de app_name.

    El runtime construye nombres de proceso, unidad systemd, `.desktop`, rutas
    `/etc/<id>/` y comandos de bandeja a partir de `get_app_name().to_lowercase()`.
    Con un app_name con espacio ('fontis remote') esos comandos se parten y el
    servicio desatendido / la bandeja fallan. El empaquetado Linux (build.py)
    instala todo como 'rustdesk' y NO se renombra, así que el identificador
    interno correcto es 'rustdesk' (idéntico al comportamiento upstream). El
    nombre visible sigue siendo APP_NAME vía get_app_name() sin lowercase.
    """
    text = LINUX_RS.read_text(encoding="utf-8")
    expr = "crate::get_app_name().to_lowercase()"
    old_flatpak = (
        '                let app_name = crate::get_app_name();\n'
        '                format!("com.{}.{}.desktop", app_name.to_lowercase(), app_name)'
    )
    new_flatpak = '                "com.rustdesk.RustDesk.desktop".to_owned()'
    changed = False
    if expr in text:
        text = text.replace(expr, '"rustdesk".to_owned()')
        changed = True
    if old_flatpak in text:
        text = text.replace(old_flatpak, new_flatpak)
        changed = True
    if changed:
        LINUX_RS.write_text(text, encoding="utf-8")
        applied.append("Linux: identificador interno fijado a 'rustdesk'")
    else:
        applied.append("Linux: identificador interno  (ya aplicado)")


def patch_windows_install_rename(env: dict) -> None:
    """Arregla el instalador GUI (install_me) para que renombre el exe.

    install_me copia el binario (rustdesk.exe) pero, a diferencia del path del
    MSI, NO llamaba a rename_exe_cmd. Con un app_name distinto de 'rustdesk' el
    exe quedaba como rustdesk.exe mientras los accesos directos, el
    desinstalador y el registro apuntaban a '<AppName>.exe' (inexistente).
    Se inserta {rename_exe} tras {copy_exe}, igual que el path del MSI.
    """
    text = WINDOWS_RS.read_text(encoding="utf-8")
    if "{copy_exe}\n{rename_exe}\nreg add {subkey} /f" in text:
        applied.append("Windows install_me: rename del exe  (ya aplicado)")
        return
    patch(
        WINDOWS_RS,
        re.escape("{copy_exe}\nreg add {subkey} /f"),
        "{copy_exe}\n{rename_exe}\nreg add {subkey} /f",
        "Windows install_me: insertar {rename_exe} en el script",
    )
    patch(
        WINDOWS_RS,
        re.escape("        copy_exe = copy_exe_cmd(&src_exe, &exe, &path)?,\n"
                  "        import_config = get_import_config(&exe),"),
        "        copy_exe = copy_exe_cmd(&src_exe, &exe, &path)?,\n"
        "        rename_exe = rename_exe_cmd(&src_exe, &path)?,\n"
        "        import_config = get_import_config(&exe),",
        "Windows install_me: arg rename_exe",
    )


def patch_ci_triggers(env: dict) -> None:
    """Ajustes de CI del fork: permiso para crear Releases y menos disparadores.

    - flutter-tag.yml / flutter-nightly.yml: `permissions: contents: write`
      (necesario para publicar el Release si el default de la organización es
      solo-lectura).
    - flutter-nightly.yml: cron nocturno desactivado (no gastar minutos).
    - fdroid.yml: solo manual (no publicamos en F-Droid).
    """
    wf = SRC / ".github" / "workflows"
    tag_yml = wf / "flutter-tag.yml"
    nightly_yml = wf / "flutter-nightly.yml"
    fdroid_yml = wf / "fdroid.yml"

    def replace_once(path, old, new, desc):
        text = path.read_text(encoding="utf-8")
        if new in text:
            applied.append(f"{desc}  (ya aplicado)")
            return
        if old not in text:
            fail(f"{desc}: no se encontró el ancla en {path} (¿cambió upstream?)")
        path.write_text(text.replace(old, new, 1), encoding="utf-8")
        applied.append(f"{desc}  ->  {path.relative_to(PROJECT_ROOT)}")

    replace_once(
        tag_yml,
        "  run-flutter-tag-build:\n    uses: ./.github/workflows/flutter-build.yml",
        "  run-flutter-tag-build:\n    permissions:\n      contents: write\n"
        "    uses: ./.github/workflows/flutter-build.yml",
        "CI: permiso contents:write en flutter-tag",
    )
    replace_once(
        nightly_yml,
        "on:\n  schedule:\n    # schedule build every night\n    - cron: \"0 0 * * *\"\n"
        "  workflow_dispatch:\n\njobs:\n  run-flutter-nightly-build:\n"
        "    uses: ./.github/workflows/flutter-build.yml",
        "on:\n  # Fontis: cron nocturno desactivado para no gastar minutos de Actions.\n"
        "  workflow_dispatch:\n\njobs:\n  run-flutter-nightly-build:\n"
        "    permissions:\n      contents: write\n"
        "    uses: ./.github/workflows/flutter-build.yml",
        "CI: nightly sin cron + permiso contents:write",
    )
    replace_once(
        fdroid_yml,
        "on:\n  workflow_dispatch:\n  push:\n    tags:\n"
        "      - 'v[0-9]+.[0-9]+.[0-9]+'\n      - '[0-9]+.[0-9]+.[0-9]+'\n"
        "      - 'v[0-9]+.[0-9]+.[0-9]+-[0-9]+'\n      - '[0-9]+.[0-9]+.[0-9]+-[0-9]+'",
        "on:\n  # Fontis: solo manual; no publicamos en F-Droid.\n  workflow_dispatch:",
        "CI: fdroid solo manual",
    )


def patch_ci_resilience(env: dict) -> None:
    """Descarga del motor Flutter custom (Windows) con reintentos.

    El paso upstream usa un Invoke-WebRequest de una sola pasada; las descargas
    grandes desde github.com/rustdesk/engine fallan de forma intermitente
    ('response ended prematurely' / 'socket hang up') y tumban todo el build de
    Windows. Se envuelve en un bucle de reintentos.
    """
    marker = "reintento descarga engine"
    text = FLUTTER_BUILD_YML.read_text(encoding="utf-8")
    if marker in text:
        applied.append("CI: reintentos descarga engine Windows  (ya aplicado)")
        return
    old = (
        "          Invoke-WebRequest -Uri "
        "https://github.com/rustdesk/engine/releases/download/main/"
        "windows-x64-release.zip -OutFile windows-x64-release.zip"
    )
    new = (
        "          for ($i=1; $i -le 5; $i++) {\n"
        "            try { Invoke-WebRequest -Uri https://github.com/rustdesk/engine/"
        "releases/download/main/windows-x64-release.zip -OutFile windows-x64-release.zip; break }\n"
        "            catch { if ($i -eq 5) { throw }; "
        "Write-Host \"reintento descarga engine $i\"; Start-Sleep -Seconds 15 }\n"
        "          }"
    )
    patch(FLUTTER_BUILD_YML, re.escape(old), new,
          "CI: reintentos descarga engine Windows")


def patch_macos_bundle(env: dict) -> None:
    """Renombra el bundle macOS a '<APP_NAME>.app' (por defecto RustDesk.app).

    Cambia PRODUCT_NAME (nombre del .app y del ejecutable interno) y ajusta las
    referencias 'RustDesk.app' del CI y del proyecto Xcode, con comillas porque
    el nombre lleva espacio.
    """
    app_name = env["APP_NAME"]

    def rename(path, pattern, repl, marker, desc, count=0, flags=0):
        """patch() idempotente: si ya está el marcador y no queda el patrón, salta."""
        text = path.read_text(encoding="utf-8")
        if marker in text and not re.search(pattern, text, flags):
            applied.append(f"{desc}  (ya aplicado)")
            return
        patch(path, pattern, repl, desc, count=count, flags=flags)

    # PRODUCT_NAME (regex sobre cualquier valor: idempotente de por sí)
    patch(
        MACOS_XCCONFIG,
        r'^PRODUCT_NAME = .*$',
        f'PRODUCT_NAME = {app_name}',
        "macOS: PRODUCT_NAME del bundle",
        flags=re.MULTILINE,
    )
    # create-dmg --icon "RustDesk.app" y --hide-extension "RustDesk.app"
    rename(
        FLUTTER_BUILD_YML, r'"RustDesk\.app"', f'"{app_name}.app"',
        f'"{app_name}.app"', "macOS CI: nombre del .app en create-dmg",
    )
    # Rutas del .app pasadas a create-dmg/codesign (con comillas por el espacio)
    rename(
        FLUTTER_BUILD_YML,
        r'\./flutter/build/macos/Build/Products/Release/RustDesk\.app',
        f'"./flutter/build/macos/Build/Products/Release/{app_name}.app"',
        f'Release/{app_name}.app"', "macOS CI: ruta del .app",
    )
    # Referencia del producto en el proyecto Xcode
    rename(
        MACOS_PBXPROJ, r'path = RustDesk\.app;', f'path = "{app_name}.app";',
        f'path = "{app_name}.app";', "macOS: product reference en project.pbxproj",
        count=1,
    )
    # BuildableName del scheme (flutter localiza el .app por aquí)
    rename(
        MACOS_XCSCHEME, r'BuildableName = "RustDesk\.app"',
        f'BuildableName = "{app_name}.app"',
        f'BuildableName = "{app_name}.app"', "macOS: BuildableName en el scheme",
    )
    # build.py copia el binario `service` dentro del .app; ruta hardcoded
    # RustDesk.app (con comillas para el shell por el espacio)
    rename(
        BUILD_PY,
        r'\./build/macos/Build/Products/Release/RustDesk\.app/Contents/MacOS/',
        f'"./build/macos/Build/Products/Release/{app_name}.app/Contents/MacOS/"',
        f'Release/{app_name}.app/Contents/MacOS/',
        "macOS: ruta del .app en build.py (copia del service)",
        count=1,
    )


def patch_server_lock(env: dict) -> None:
    lock = env.get("LOCK_SERVER_SETTINGS", "false").lower() == "true"
    pattern = r'pub static ref OVERWRITE_SETTINGS: RwLock<HashMap<String, String>> =[^;]*;'
    if lock:
        entries = [
            ("custom-rendezvous-server", env["RENDEZVOUS_SERVER"]),
            ("key", env["RS_PUB_KEY"]),
        ]
        if env.get("API_SERVER"):
            entries.append(("api-server", env["API_SERVER"]))
        rust_entries = ", ".join(
            f'("{rust_str(k)}".to_owned(), "{rust_str(v)}".to_owned())' for k, v in entries
        )
        replacement = (
            "pub static ref OVERWRITE_SETTINGS: RwLock<HashMap<String, String>> = "
            f"RwLock::new(HashMap::from([{rust_entries}]));"
        )
        desc = "Servidor bloqueado en ajustes (OVERWRITE_SETTINGS)"
    else:
        replacement = (
            "pub static ref OVERWRITE_SETTINGS: RwLock<HashMap<String, String>> = "
            "Default::default();"
        )
        desc = "Servidor editable en ajustes (OVERWRITE_SETTINGS por defecto)"
    patch(CONFIG_RS, pattern, replacement, desc)


# ----------------------------------------------------------------------------
# Iconos y logo
# ----------------------------------------------------------------------------

def find_asset(name: str):
    for base in (ICONS_DIR, PROJECT_ROOT):
        candidate = base / name
        if candidate.exists():
            return candidate
    return None


def patch_icons(env: dict) -> None:
    try:
        from PIL import Image
    except ImportError:
        warnings.append(
            "Pillow no está instalado (python -m pip install pillow): iconos NO generados."
        )
        return

    logo_name = env.get("LOGO_FILE", "logo_fontis_primary.png")
    logo_path = find_asset(logo_name)
    icon_path = find_asset("icon-1024.png")

    if icon_path is None and logo_path is None:
        warnings.append("Sin logo ni icono en branding/icons/: se conservan los de RustDesk.")
        return

    if icon_path is not None:
        master = Image.open(icon_path).convert("RGBA")
    else:
        # Placeholder: logo centrado en lienzo cuadrado transparente.
        logo = Image.open(logo_path).convert("RGBA")
        side = 1024
        master = Image.new("RGBA", (side, side), (0, 0, 0, 0))
        scale = min(side * 0.86 / logo.width, side * 0.86 / logo.height)
        resized = logo.resize(
            (max(1, round(logo.width * scale)), max(1, round(logo.height * scale))),
            Image.LANCZOS,
        )
        master.paste(resized, ((side - resized.width) // 2, (side - resized.height) // 2), resized)
        warnings.append(
            "Icono cuadrado generado como PLACEHOLDER a partir del logo horizontal. "
            "Para producción, añade branding/icons/icon-1024.png (1024x1024)."
        )

    def save_png(target: Path, size: int) -> None:
        master.resize((size, size), Image.LANCZOS).save(target, format="PNG")
        applied.append(f"Icono {size}x{size}  ->  {target.relative_to(PROJECT_ROOT)}")

    def save_ico(target: Path) -> None:
        base = master.resize((256, 256), Image.LANCZOS)
        base.save(target, format="ICO",
                  sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
        applied.append(f"Icono ICO  ->  {target.relative_to(PROJECT_ROOT)}")

    res = SRC / "res"
    save_png(res / "icon.png", 1024)
    save_png(res / "mac-icon.png", 1024)
    save_png(res / "32x32.png", 32)
    save_png(res / "64x64.png", 64)
    save_png(res / "128x128.png", 128)
    save_png(res / "128x128@2x.png", 256)
    save_png(SRC / "flutter" / "assets" / "icon.png", 256)

    save_ico(res / "icon.ico")
    save_ico(res / "tray-icon.ico")
    save_ico(SRC / "flutter" / "windows" / "runner" / "resources" / "app_icon.ico")

    # ICNS para macOS con varias resoluciones
    icns_target = SRC / "flutter" / "macos" / "Runner" / "AppIcon.icns"
    icns_sizes = [512, 256, 128, 64, 32, 16]
    master.resize((1024, 1024), Image.LANCZOS).save(
        icns_target, format="ICNS",
        append_images=[master.resize((s, s), Image.LANCZOS) for s in icns_sizes],
    )
    applied.append(f"Icono ICNS  ->  {icns_target.relative_to(PROJECT_ROOT)}")

    # Iconos de bandeja de macOS (mantener dimensiones originales)
    for tray_name in ("mac-tray-dark-x2.png", "mac-tray-light-x2.png"):
        tray_target = res / tray_name
        if tray_target.exists():
            w, h = Image.open(tray_target).size
            master.resize((w, h), Image.LANCZOS).save(tray_target, format="PNG")
            applied.append(f"Icono bandeja macOS  ->  {tray_target.relative_to(PROJECT_ROOT)}")

    # Logo de cabecera dentro de la app (máx 300x60, BoxFit.contain)
    if logo_path is not None:
        assets = SRC / "flutter" / "assets"
        logo = Image.open(logo_path).convert("RGBA")
        logo.save(assets / "logo.png", format="PNG")
        applied.append(f"Logo de cabecera  ->  {(assets / 'logo.png').relative_to(PROJECT_ROOT)}")
        for variant, target in (("logo_light.png", "logo_light.png"),
                                ("logo_dark.png", "logo_dark.png")):
            source = find_asset(variant)
            if source is not None:
                Image.open(source).convert("RGBA").save(assets / target, format="PNG")
                applied.append(f"Logo ({variant})  ->  {(assets / target).relative_to(PROJECT_ROOT)}")


# ----------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-placeholders", action="store_true",
                        help="Permite valores CAMBIAR_* (solo para probar el script)")
    parser.add_argument("--skip-icons", action="store_true",
                        help="No toca iconos ni logo")
    args = parser.parse_args()

    if not SRC.exists():
        fail(f"No existe {SRC}. Clona primero el código fuente de RustDesk.")
    if not CONFIG_RS.exists():
        fail(f"No existe {CONFIG_RS}. Inicializa el submódulo: "
             "git -C rustdesk submodule update --init")

    env = load_env(ENV_FILE)
    for required in ("APP_NAME", "RENDEZVOUS_SERVER", "RS_PUB_KEY"):
        if not env.get(required):
            fail(f"Falta {required} en {ENV_FILE}")
    placeholders = [k for k, v in env.items() if "CAMBIAR" in v]
    if placeholders and not args.allow_placeholders:
        fail(
            f"Estos valores de {ENV_FILE.name} siguen sin rellenar: {', '.join(placeholders)}.\n"
            "  Rellénalos con los datos reales del servidor (o usa --allow-placeholders "
            "solo para probar)."
        )

    patch_server(env)
    patch_app_name(env)
    patch_gitignore(env)
    patch_readme_header(env)
    patch_readme_urls(env)
    patch_readme_cleanup(env)
    patch_windows_packaging(env)
    patch_windows_install_rename(env)
    patch_linux_app_id(env)
    patch_service_recovery(env)
    patch_ci_triggers(env)
    patch_ci_resilience(env)
    patch_macos_bundle(env)
    patch_server_lock(env)
    if not args.skip_icons:
        patch_icons(env)

    print("\n=== Branding aplicado ===")
    for line in applied:
        print(f"  [ok] {line}")
    if placeholders:
        warnings.append(
            f"El árbol contiene PLACEHOLDERS ({', '.join(placeholders)}): NO compilar así."
        )
    if warnings:
        print("\n=== Avisos ===")
        for line in warnings:
            print(f"  [!] {line}")
    print(f"\nRevisa los cambios con:  git -C rustdesk diff  (y dentro de libs/hbb_common)")


if __name__ == "__main__":
    main()
