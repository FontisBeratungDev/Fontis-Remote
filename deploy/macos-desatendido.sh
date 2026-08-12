#!/bin/bash
# =====================================================================
# Acceso desatendido de Fontis Remote en macOS
# =====================================================================
# Bloques (flags):
#   --set-password <clave>   Contraseña permanente de Fontis Remote.
#   --auto-login <user> <pass>  macOS inicia sesión solo al arrancar.
#   --no-lock                No pedir contraseña al despertar / sin salvapantallas.
#
# Ejecutar con sudo (auto-login y no-lock lo requieren).
#
# ⚠️ SEGURIDAD:
#   - Auto-login en macOS NO funciona con FileVault activado (el disco pide
#     contraseña al arrancar). Desactivar FileVault = disco SIN cifrar. Solo en
#     equipos físicamente seguros.
#   - Fontis Remote necesita permisos de "Grabación de pantalla" y
#     "Accesibilidad" (Ajustes del Sistema > Privacidad). En flota, empujar por
#     MDM con un perfil PPPC (Jamf / Intune / Mosyle).
#   - Acceso a la pantalla de login (loginwindow) en macOS es limitado; el caso
#     fiable es: sesión iniciada (auto-login) + sin bloqueo.

set -euo pipefail

APP="/Applications/Fontis Remote.app/Contents/MacOS/Fontis Remote"
SET_PASSWORD=""
AUTO_USER=""
AUTO_PASS=""
NO_LOCK=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --set-password) SET_PASSWORD="$2"; shift 2 ;;
    --auto-login)   AUTO_USER="$2"; AUTO_PASS="$3"; shift 3 ;;
    --no-lock)      NO_LOCK=1; shift ;;
    *) echo "Opción desconocida: $1"; exit 1 ;;
  esac
done

# --- Contraseña permanente de Fontis Remote --------------------------
if [[ -n "$SET_PASSWORD" ]]; then
  if [[ ! -x "$APP" ]]; then echo "No existe $APP (¿instalado?)"; exit 1; fi
  "$APP" --password "$SET_PASSWORD"
  echo "[ok] Contraseña permanente de Fontis Remote establecida."
fi

# --- Auto-login de macOS (AutoAdminLogon equivalente) ----------------
if [[ -n "$AUTO_USER" ]]; then
  if [[ "$(fdesetup status | grep -c 'FileVault is On')" -ge 1 ]]; then
    echo "⚠️  FileVault ACTIVO: el auto-login no surtirá efecto hasta desactivarlo"
    echo "    (sudo fdesetup disable). Deja el disco SIN cifrar — decide con cuidado."
  fi
  # sysadminctl gestiona /etc/kcpassword de forma soportada
  sudo sysadminctl -autologin set -userName "$AUTO_USER" -password "$AUTO_PASS"
  echo "[ok] Auto-login de macOS configurado para '$AUTO_USER'."
fi

# --- Sin bloqueo por inactividad -------------------------------------
if [[ "$NO_LOCK" -eq 1 ]]; then
  # No pedir contraseña tras salvapantallas/suspensión (usuario actual)
  defaults -currentHost write com.apple.screensaver askForPassword -int 0
  defaults -currentHost write com.apple.screensaver idleTime -int 0
  # No suspender (equipo conectado a corriente)
  sudo pmset -a sleep 0 displaysleep 0
  echo "[ok] Bloqueo por inactividad y suspensión desactivados."
  echo "     NOTA: si el equipo SUSPENDE seguirá inalcanzable en remoto."
fi

if [[ -z "$SET_PASSWORD" && -z "$AUTO_USER" && "$NO_LOCK" -eq 0 ]]; then
  echo "Nada que hacer. Usa --set-password / --auto-login / --no-lock."
fi
