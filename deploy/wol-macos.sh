#!/bin/bash
# =====================================================================
# Habilita Wake-on-LAN en macOS para Fontis Remote
# =====================================================================
# Ejecutar con sudo. Activa "Wake for network access" (Wake on Magic Packet).
#
# ⚠️ Recordatorio: WoL necesita OTRO Fontis Remote encendido en la MISMA LAN
#    que envie el paquete. Un Mac dormido no se despierta por internet solo.
#
# Limitaciones macOS:
#   - Fiable por ETHERNET (o adaptador Thunderbolt/USB-Ethernet). Por Wi-Fi es
#     poco fiable (requiere Bonjour Sleep Proxy: Apple TV/router compatible).
#   - Funciona desde SUSPENSION, no desde apagado.
#   - Portatiles con la tapa cerrada: WoL limitado (mejor con corriente + Ethernet).

set -euo pipefail

if [[ "$(id -u)" -ne 0 ]]; then echo "Ejecuta con sudo."; exit 1; fi

# Wake on Magic Packet (womp) para todos los modos de energia
pmset -a womp 1

echo "[ok] Wake for network access habilitado."
echo "Estado:"
pmset -g | grep -i womp || echo "  (womp no listado: la Mac puede no soportarlo por este medio)"
echo ""
echo "GUI equivalente: Ajustes del Sistema > Energia > 'Despertar para acceso de red'."
