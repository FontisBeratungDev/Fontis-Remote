#!/bin/bash
# =====================================================================
# Acceso desatendido de Fontis Remote en Linux
# =====================================================================
# Bloques (flags):
#   --set-password <clave>   Contraseña permanente de Fontis Remote.
#   --auto-login <user>      El gestor de pantalla inicia sesión solo.
#   --no-sleep               Impedir suspensión/hibernación.
#
# Ejecutar con sudo (auto-login y no-sleep lo requieren).
# Detecta GDM / LightDM / SDDM automáticamente.
#
# ⚠️ IMPORTANTE — Wayland vs X11:
#   El acceso desatendido de RustDesk/Fontis (captura + inyección de teclado
#   y ratón, y la pantalla de login) es fiable en X11, NO en Wayland. Para GDM,
#   este script pone WaylandEnable=false (requiere reiniciar). En KDE/otros,
#   elige "sesión X11/Xorg" en el login.
#
# ⚠️ SEGURIDAD: el auto-login del gestor de pantalla entra al escritorio sin
#   contraseña. Solo en equipos físicamente seguros; considera cifrado de disco
#   (LUKS pide clave al arrancar, incompatible con arranque 100% desatendido).

set -euo pipefail

RUSTDESK_BIN="$(command -v rustdesk || echo /usr/bin/rustdesk)"
SET_PASSWORD=""
AUTO_USER=""
NO_SLEEP=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --set-password) SET_PASSWORD="$2"; shift 2 ;;
    --auto-login)   AUTO_USER="$2"; shift 2 ;;
    --no-sleep)     NO_SLEEP=1; shift ;;
    *) echo "Opción desconocida: $1"; exit 1 ;;
  esac
done

# --- Contraseña permanente de Fontis Remote --------------------------
if [[ -n "$SET_PASSWORD" ]]; then
  if [[ ! -x "$RUSTDESK_BIN" ]]; then echo "No se encuentra el binario rustdesk"; exit 1; fi
  "$RUSTDESK_BIN" --password "$SET_PASSWORD"
  echo "[ok] Contraseña permanente de Fontis Remote establecida."
fi

# --- Auto-login del gestor de pantalla -------------------------------
if [[ -n "$AUTO_USER" ]]; then
  if [[ -f /etc/gdm3/custom.conf || -f /etc/gdm/custom.conf ]]; then
    CONF=$([[ -f /etc/gdm3/custom.conf ]] && echo /etc/gdm3/custom.conf || echo /etc/gdm/custom.conf)
    # Inserta bajo [daemon]: AutomaticLoginEnable, AutomaticLogin, WaylandEnable=false
    sudo sed -i '/^\[daemon\]/a AutomaticLoginEnable=true\nAutomaticLogin='"$AUTO_USER"'\nWaylandEnable=false' "$CONF"
    echo "[ok] GDM: auto-login de '$AUTO_USER' + Wayland desactivado en $CONF."
  elif [[ -d /etc/lightdm ]]; then
    sudo mkdir -p /etc/lightdm/lightdm.conf.d
    printf '[Seat:*]\nautologin-user=%s\nautologin-user-timeout=0\n' "$AUTO_USER" \
      | sudo tee /etc/lightdm/lightdm.conf.d/50-fontis-autologin.conf >/dev/null
    echo "[ok] LightDM: auto-login de '$AUTO_USER'."
  elif [[ -f /etc/sddm.conf || -d /etc/sddm.conf.d ]]; then
    sudo mkdir -p /etc/sddm.conf.d
    printf '[Autologin]\nUser=%s\nSession=plasmax11.desktop\n' "$AUTO_USER" \
      | sudo tee /etc/sddm.conf.d/50-fontis-autologin.conf >/dev/null
    echo "[ok] SDDM: auto-login de '$AUTO_USER' (sesión X11)."
  else
    echo "⚠️  No se detectó GDM/LightDM/SDDM. Configura el auto-login del gestor manualmente."
  fi
  echo "     Reinicia para aplicar."
fi

# --- Impedir suspensión ----------------------------------------------
if [[ "$NO_SLEEP" -eq 1 ]]; then
  sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target
  echo "[ok] Suspensión/hibernación deshabilitadas."
fi

# --- Recordatorio: bloqueo de pantalla (sesión de escritorio) --------
if [[ -n "$AUTO_USER" ]]; then
  cat <<EOF

Para quitar el bloqueo por inactividad, ejecuta EN LA SESIÓN del usuario
'$AUTO_USER' (no como root), en GNOME:

  gsettings set org.gnome.desktop.screensaver lock-enabled false
  gsettings set org.gnome.desktop.session idle-delay 0

(KDE: Ajustes del Sistema > Bloqueo de pantalla > desactivar.)
EOF
fi

if [[ -z "$SET_PASSWORD" && -z "$AUTO_USER" && "$NO_SLEEP" -eq 0 ]]; then
  echo "Nada que hacer. Usa --set-password / --auto-login / --no-sleep."
fi
