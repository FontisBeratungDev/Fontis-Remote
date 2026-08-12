<#
.SYNOPSIS
    Configura acceso desatendido de Fontis Remote en un equipo Windows.

.DESCRIPTION
    Tres bloques independientes (actívalos con los switches):
      -SetPassword   Fija la contraseña permanente de Fontis Remote (acceso remoto).
      -AutoLogin     Windows inicia sesión solo al arrancar/despertar (AutoAdminLogon).
      -NoLock        El equipo no se bloquea por inactividad (queda siempre en el escritorio).

    "Login en pantalla bloqueada" (escribir la clave de Windows en remoto) NO
    necesita nada de esto: ya funciona con el servicio instalado + contraseña
    permanente. Usa solo -SetPassword para ese caso.

    Ejecutar como Administrador. Pensado para lanzarse por equipo, o por
    GPO/Intune (script de inicio) en la flota.

.EXAMPLE
    # Solo acceso remoto en pantalla bloqueada (recomendado por defecto):
    .\windows-desatendido.ps1 -SetPassword -RemotePassword 'ClaveRemota123'

.EXAMPLE
    # Equipo que debe quedar SIEMPRE en el escritorio, sin manos:
    .\windows-desatendido.ps1 -SetPassword -RemotePassword 'ClaveRemota123' `
        -AutoLogin -WinUser 'soporte' -WinPassword 'ClaveWindows' -NoLock

.NOTES
    ⚠️ SEGURIDAD (-AutoLogin / -NoLock): eliminan el control de acceso principal
    de Windows. Solo en equipos físicamente seguros y con BitLocker activo.
    Ver deploy/acceso-desatendido.md.
#>

[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
param(
    [switch]$SetPassword,
    [string]$RemotePassword,

    [switch]$AutoLogin,
    [string]$WinUser,
    [string]$WinPassword,
    [string]$WinDomain = $env:COMPUTERNAME,

    [switch]$NoLock,

    [string]$ServiceName = 'Fontis Remote',
    [string]$ExePath = 'C:\Program Files\Fontis Remote\Fontis Remote.exe'
)

$ErrorActionPreference = 'Stop'

function Assert-Admin {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    $p = New-Object Security.Principal.WindowsPrincipal($id)
    if (-not $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'Ejecuta este script como Administrador.'
    }
}

function Ensure-Service {
    $svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if (-not $svc) {
        Write-Warning "Servicio '$ServiceName' no encontrado. ¿Está instalado Fontis Remote (no la versión portable)?"
        return
    }
    if ($svc.Status -ne 'Running') { Start-Service $ServiceName }
    Set-Service -Name $ServiceName -StartupType Automatic
    Write-Host "[ok] Servicio '$ServiceName' activo y en arranque automático."
}

function Set-RemotePassword {
    if (-not (Test-Path $ExePath)) { throw "No existe el ejecutable: $ExePath" }
    if (-not $RemotePassword) { throw 'Falta -RemotePassword.' }
    & $ExePath --password $RemotePassword
    Write-Host '[ok] Contraseña permanente de Fontis Remote establecida.'
}

function Set-AutoLogin {
    if (-not $WinUser -or -not $WinPassword) { throw 'Falta -WinUser / -WinPassword.' }
    Write-Warning 'AutoAdminLogon: el equipo iniciará sesión de Windows SIN pedir contraseña.'
    if (-not $PSCmdlet.ShouldProcess("$WinDomain\$WinUser", 'Configurar AutoAdminLogon')) { return }

    $winlogon = 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon'

    # Método preferido: Sysinternals Autologon (guarda la clave cifrada como
    # secreto LSA, NO en texto plano). Si autologon64.exe está junto al script.
    $autologonExe = Join-Path $PSScriptRoot 'autologon64.exe'
    if (Test-Path $autologonExe) {
        & $autologonExe /accepteula $WinUser $WinDomain $WinPassword | Out-Null
        Write-Host '[ok] AutoAdminLogon configurado con Sysinternals (clave cifrada en LSA).'
    }
    else {
        # Respaldo: registro clásico. DefaultPassword queda en TEXTO PLANO.
        Write-Warning 'Sin autologon64.exe: se usa el registro (DefaultPassword en texto plano). Descarga Sysinternals Autologon para cifrarla.'
        Set-ItemProperty $winlogon 'AutoAdminLogon' '1' -Type String
        Set-ItemProperty $winlogon 'DefaultUserName' $WinUser -Type String
        Set-ItemProperty $winlogon 'DefaultDomainName' $WinDomain -Type String
        Set-ItemProperty $winlogon 'DefaultPassword' $WinPassword -Type String
        Write-Host '[ok] AutoAdminLogon configurado por registro.'
    }
}

function Set-NoLock {
    if (-not $PSCmdlet.ShouldProcess($env:COMPUTERNAME, 'Deshabilitar bloqueo de sesión')) { return }

    # Deshabilita el bloqueo manual (Win+L / Ctrl+Alt+Supr -> Bloquear)
    $polSystem = 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System'
    if (-not (Test-Path $polSystem)) { New-Item $polSystem -Force | Out-Null }
    Set-ItemProperty $polSystem 'DisableLockWorkstation' 1 -Type DWord

    # No pedir contraseña al despertar de la suspensión (plan activo)
    powercfg /SETACVALUEINDEX SCHEME_CURRENT SUB_NONE CONSOLELOCK 0 2>$null
    powercfg /SETDCVALUEINDEX SCHEME_CURRENT SUB_NONE CONSOLELOCK 0 2>$null
    powercfg /SETACTIVE SCHEME_CURRENT 2>$null

    # Salvapantallas sin contraseña (equipo actual)
    Set-ItemProperty 'HKCU:\Control Panel\Desktop' 'ScreenSaverIsSecure' '0' -Type String -ErrorAction SilentlyContinue

    Write-Host '[ok] Bloqueo por inactividad deshabilitado.'
    Write-Host '     NOTA: si el equipo SUSPENDE seguirá inalcanzable. Para evitarlo:'
    Write-Host '           powercfg /change standby-timeout-ac 0'
}

Assert-Admin
Ensure-Service
if ($SetPassword) { Set-RemotePassword }
if ($AutoLogin) { Set-AutoLogin }
if ($NoLock) { Set-NoLock }
if (-not ($SetPassword -or $AutoLogin -or $NoLock)) {
    Write-Host 'Nada que hacer. Pasa -SetPassword y/o -AutoLogin y/o -NoLock. Ver -? para ayuda.'
}
