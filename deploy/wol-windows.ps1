<#
.SYNOPSIS
    Habilita Wake-on-LAN en un equipo Windows para Fontis Remote.

.DESCRIPTION
    Configura la tarjeta de red para despertar con "paquete mágico" y desactiva
    el Inicio rápido (que rompe WoL). Ejecutar como Administrador.

    ⚠️ Ademas hay que habilitar Wake-on-LAN en la BIOS/UEFI del equipo
    (suele llamarse "Power On by PCI-E/PCI", "Wake on LAN", "Resume by LAN").
    Eso NO se puede hacer por script; es manual o por herramienta del fabricante.

    Recordatorio: WoL necesita OTRO Fontis Remote encendido en la MISMA LAN que
    envie el paquete. Un equipo dormido no se despierta por internet solo.
#>

[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'

$id = [Security.Principal.WindowsIdentity]::GetCurrent()
if (-not (New-Object Security.Principal.WindowsPrincipal($id)).IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Ejecuta como Administrador.'
}

# NIC física activa
$nic = Get-NetAdapter -Physical | Where-Object Status -eq 'Up' | Select-Object -First 1
if (-not $nic) { throw 'No hay tarjeta de red activa.' }
Write-Host "Tarjeta: $($nic.Name) ($($nic.InterfaceDescription))"

# 1. Permitir que el dispositivo despierte el equipo con paquete magico
try {
    Set-NetAdapterPowerManagement -Name $nic.Name -WakeOnMagicPacket Enabled -ErrorAction Stop
    Write-Host '[ok] Wake on Magic Packet habilitado en la tarjeta.'
} catch {
    Write-Warning "La tarjeta no expone WakeOnMagicPacket via PowerShell; revisa Administrador de dispositivos -> $($nic.Name) -> Administracion de energia."
}

# 2. Registrar el dispositivo como habilitado para despertar
try { powercfg /deviceenablewake "$($nic.InterfaceDescription)" 2>$null; Write-Host '[ok] Dispositivo habilitado para despertar (powercfg).' } catch {}

# 3. Desactivar Inicio rapido (hybrid shutdown rompe WoL desde apagado)
reg add "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Power" `
    /v HiberbootEnabled /t REG_DWORD /d 0 /f | Out-Null
Write-Host '[ok] Inicio rapido desactivado.'

Write-Host ''
Write-Host 'FALTA: habilitar Wake-on-LAN en la BIOS/UEFI del equipo (manual).'
Write-Host 'Verifica que quedo armado:  powercfg /devicequery wake_armed'
