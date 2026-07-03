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

PROJECT_ROOT = Path(__file__).resolve().parent.parent
# Dos disposiciones posibles: proyecto local (fuente en ./rustdesk) o
# ejecución dentro del propio fork (fuente en la raíz del repo).
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
