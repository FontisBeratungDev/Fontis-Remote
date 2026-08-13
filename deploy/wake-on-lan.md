# Wake-on-LAN (encender un equipo dormido)

Igual que RealVNC. **Fontis Remote ya lo trae** (`lan::send_wol`): no es código
nuevo. Un equipo suspendido/hibernando tiene la CPU parada y **no se despierta
solo por internet**; hay que enviarle un "paquete mágico" (Wake-on-LAN).

## Cómo funciona

1. Otro Fontis Remote **encendido en la misma red local (LAN)** que el equipo
   dormido envía el paquete mágico.
2. Desde el descubrimiento de red / lista de equipos, se dispara "Wake on LAN"
   sobre el equipo dormido (su MAC ya está cacheada tras haberlo visto en la LAN).
3. Para despertar **desde fuera** (internet): conéctate primero a un equipo
   despierto de esa LAN y desde él despierta al dormido.

Requisito ineludible: siempre debe haber **un equipo encendido en la LAN** del
objetivo (RealVNC tiene exactamente la misma limitación).

## Habilitar WoL en el equipo objetivo (una vez)

Tres capas, todas necesarias:

### 1. BIOS/UEFI (manual)
Activar "Wake on LAN" / "Power On by PCI-E" / "Resume by LAN". No se puede por
script; es la config de arranque del equipo.

### 2. Tarjeta de red + Inicio rápido
- **Windows**: ejecutar [wol-windows.ps1](wol-windows.ps1) como administrador
  (habilita "Wake on Magic Packet" en la NIC, arma el dispositivo y desactiva el
  Inicio rápido). Verificar: `powercfg /devicequery wake_armed`.
- **macOS**: ejecutar [wol-macos.sh](wol-macos.sh) con `sudo` (`pmset -a womp 1`),
  o Ajustes del Sistema → Energía → "Despertar para acceso de red". Fiable por
  **Ethernet**; por Wi-Fi necesita un Bonjour Sleep Proxy (Apple TV / router
  compatible). Solo desde suspensión, no desde apagado; portátiles con tapa
  cerrada, limitado.
- **Linux**: `sudo ethtool -s <interfaz> wol g` (persistir en el gestor de red o
  un servicio systemd; requiere que la NIC soporte WoL — `ethtool <if> | grep Wake`).

### 3. El emisor
El equipo que despierta al dormido debe ser otro Fontis Remote encendido en la
misma LAN. En sitios con varios equipos, cualquiera encendido sirve de emisor.

## Limitaciones

- WoL desde **hibernación (S4)** y apagado (S5) depende de la BIOS/NIC; desde
  **suspensión (S3)** funciona casi siempre con lo de arriba.
- Redes con VLANs / Wi-Fi: WoL por Wi-Fi (WoWLAN) es poco fiable; va mejor por
  cable. El paquete no cruza subredes sin ayuda del router.
- Si un sitio no tiene ningún equipo encendido 24/7, no hay quien envíe el
  paquete: alternativa = un mini-PC/router con WoL siempre encendido, o dejar el
  equipo sin suspender (ver [acceso-desatendido.md](acceso-desatendido.md)).
