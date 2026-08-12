# Acceso desatendido (equivalente a RealVNC)

Objetivo: acceder a un equipo bloqueado o que arranca/despierta e **iniciar
sesión de forma automática**, como RealVNC. Todo es **configuración de Windows +
despliegue**, no cambios en Fontis Remote. Script: [windows-desatendido.ps1](windows-desatendido.ps1).

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
