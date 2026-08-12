# Acceso desatendido (equivalente a RealVNC)

Objetivo: acceder a un equipo bloqueado o que arranca/despierta e **iniciar
sesión de forma automática**, como RealVNC. Todo es **configuración del sistema +
despliegue**, no cambios en Fontis Remote. Un script por plataforma:

| SO | Script |
|---|---|
| Windows | [windows-desatendido.ps1](windows-desatendido.ps1) |
| macOS | [macos-desatendido.sh](macos-desatendido.sh) |
| Linux | [linux-desatendido.sh](linux-desatendido.sh) |

El resto del documento detalla Windows; al final están las secciones de macOS y
Linux con sus particularidades (FileVault, Wayland).

## Los tres escenarios

### 1. Login en pantalla bloqueada (ya funciona)
El servicio de Windows de Fontis Remote muestra la pantalla de login/bloqueo en
remoto. Te conectas, ves el login de Windows, escribes la contraseña y entras —
igual que RealVNC. Requisito único: servicio instalado (lo hace el .msi/.exe, no
la versión portable) + contraseña permanente de Fontis Remote.

```powershell
.\windows-desatendido.ps1 -SetPassword -RemotePassword 'ClaveRemota123'
```

### 2. Auto-login de Windows sin contraseña (AutoAdminLogon)
El equipo inicia sesión de Windows solo al arrancar/despertar. Combinado con el
punto 3, al conectarte en remoto siempre caes en el escritorio, sin escribir
nada.

```powershell
.\windows-desatendido.ps1 -SetPassword -RemotePassword 'ClaveRemota123' `
    -AutoLogin -WinUser 'soporte' -WinPassword 'ClaveWindows' -NoLock
```

### 3. No bloquear por inactividad (-NoLock)
Sin esto, aunque haya auto-login, el equipo se bloquea tras unos minutos y vuelve
a pedir contraseña. `-NoLock` desactiva el bloqueo, quita la contraseña al
despertar y el salvapantallas seguro.

## ⚠️ Seguridad (leer antes de usar -AutoLogin / -NoLock)

Auto-login + no-bloqueo **eliminan el control de acceso principal de Windows**:
cualquiera con acceso físico al equipo entra sin contraseña. Condiciones mínimas:

- **BitLocker activo** (protege los datos si roban el equipo apagado; el
  auto-login solo actúa tras desbloquear el disco al arrancar).
- Solo en equipos **físicamente seguros** (oficina con acceso controlado), nunca
  en portátiles que salen.
- Preferir una **cuenta de soporte dedicada** de bajos privilegios en vez de la
  cuenta del usuario, donde sea posible.
- Usar **Sysinternals Autologon** (`autologon64.exe` junto al script): guarda la
  contraseña **cifrada** como secreto LSA. Sin él, el script cae al registro y la
  contraseña queda en **texto plano** en `Winlogon\DefaultPassword`.
  Descarga: https://learn.microsoft.com/sysinternals/downloads/autologon

## Despliegue en la flota (dominio AD / Intune)

- **Equipos gestionados por TI** (cuentas de dominio o locales de TI): empujar el
  script como *startup script* (GPO) o script de plataforma (Intune) con las
  credenciales de la cuenta de soporte. La contraseña permanente de Fontis puede
  ir embebida en el cliente (misma para toda la flota) o fijarse por script.
- **Equipos personales** (el usuario sabe su clave): usar solo el escenario 1
  (login en pantalla bloqueada). El técnico pide la clave o entra con una cuenta
  de soporte. No aplicar auto-login en equipos personales.
- **Mezcla**: dos grupos de directiva — gestionados con `-AutoLogin -NoLock`,
  personales solo con `-SetPassword`.

## Recordatorio sobre equipos suspendidos

Auto-login y no-bloqueo NO despiertan un equipo dormido — sigue fuera de red.
Para que estén siempre accesibles, desactivar la suspensión:

```powershell
powercfg /change standby-timeout-ac 0
powercfg /change hibernate-timeout-ac 0
```

O configurar Wake-on-LAN (requiere otro equipo encendido en la misma LAN que
envíe el paquete mágico).

---

## macOS

Script: [macos-desatendido.sh](macos-desatendido.sh) (ejecutar con `sudo`).

```bash
# Solo acceso remoto (contraseña permanente):
sudo ./macos-desatendido.sh --set-password 'ClaveRemota123'

# Equipo siempre en el escritorio, sin manos:
sudo ./macos-desatendido.sh --set-password 'ClaveRemota123' \
    --auto-login soporte 'ClaveMac' --no-lock
```

Particularidades macOS:
- **FileVault vs auto-login**: el auto-login de macOS **no funciona con FileVault
  activo** (el disco pide contraseña al arrancar). Desactivarlo deja el disco
  **sin cifrar** — decisión de seguridad seria; solo en equipos físicamente
  seguros. El script avisa si FileVault está activo.
- **Permisos**: Fontis Remote necesita "Grabación de pantalla" y "Accesibilidad"
  (Ajustes del Sistema > Privacidad y seguridad). Se conceden a mano la primera
  vez, o por **MDM** (Jamf / Intune / Mosyle) con un perfil PPPC en la flota.
- **Pantalla de login**: el acceso al `loginwindow` de macOS es limitado. El caso
  fiable es sesión ya iniciada (auto-login) + sin bloqueo.
- Auto-login se aplica con `sysadminctl -autologin` (gestiona `/etc/kcpassword`
  de forma soportada).

## Linux

Script: [linux-desatendido.sh](linux-desatendido.sh) (ejecutar con `sudo`).
Detecta GDM / LightDM / SDDM.

```bash
sudo ./linux-desatendido.sh --set-password 'ClaveRemota123' \
    --auto-login soporte --no-sleep
```

Particularidades Linux:
- **Wayland vs X11**: el acceso desatendido (captura + inyección de teclado/ratón
  y pantalla de login) es fiable en **X11, no en Wayland**. Para GDM el script
  pone `WaylandEnable=false`. En KDE/otros, elige "sesión Xorg/X11" en el login.
- **Auto-login**: se configura en el gestor de pantalla (GDM/LightDM/SDDM); el
  script escribe el archivo correcto según cuál detecte. Reiniciar para aplicar.
- **Bloqueo de pantalla**: se quita desde la sesión del usuario (no root); el
  script imprime los comandos `gsettings` de GNOME (KDE: Ajustes > Bloqueo de
  pantalla).
- **Cifrado de disco**: LUKS pide clave al arrancar — incompatible con arranque
  100% desatendido, igual que FileVault/BitLocker. Valora el compromiso.

## Resumen de mecanismos por plataforma

| | Windows | macOS | Linux |
|---|---|---|---|
| Contraseña remota | `--password` | `--password` | `--password` |
| Auto-login | AutoAdminLogon | `sysadminctl -autologin` | gestor de pantalla |
| Sin bloqueo | DisableLockWorkstation | `askForPassword 0` | gsettings / DE |
| Choca con cifrado | BitLocker* | FileVault (bloquea) | LUKS (bloquea) |
| Login remoto bloqueado | ✅ servicio | limitado | X11 sí / Wayland no |

\* BitLocker con TPM desbloquea solo al arrancar, así que **sí** convive con
auto-login (recomendado). FileVault y LUKS piden clave al arranque, así que
rompen el arranque 100% desatendido.
