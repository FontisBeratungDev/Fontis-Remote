# Servicio persistente (arranca al encender, sigue activo aunque cierres)

Fontis Remote instalado (NO la versión portable) ya cumple esto vía su **servicio**:

- **Arranca al encender el equipo** — antes incluso del login.
- **Sigue activo aunque cierres la ventana/tray** — el servicio atiende conexiones
  con independencia de la GUI. Cerrar la app NO corta el acceso remoto.

Lo único que añadimos aquí es **auto-reinicio si el servicio se cae** (crash).

## Estado por plataforma

| | Arranca al boot | Persiste si cierras GUI | Auto-reinicio ante crash |
|---|---|---|---|
| Windows | ✅ servicio `start=auto` | ✅ | ⚠ añadir `sc failure` |
| macOS | ✅ `RunAtLoad` | ✅ | ✅ ya (`KeepAlive`) |
| Linux | ✅ `WantedBy=multi-user` | ✅ | ⚠ añadir `Restart=always` |

## Windows (instalaciones ya hechas)

Incluido en [windows-desatendido.ps1](windows-desatendido.ps1) (se aplica al correrlo).
Manual:

```powershell
sc.exe failure "Fontis Remote" reset= 86400 actions= restart/5000/restart/5000/restart/5000
```

## Linux (instalaciones ya hechas)

Override de systemd sin editar el paquete:

```bash
sudo systemctl edit rustdesk.service
# en el editor, pegar:
[Service]
Restart=always
RestartSec=2
# guardar, luego:
sudo systemctl daemon-reload
sudo systemctl restart rustdesk
```

(En builds nuevos ya viene `Restart=always` de fábrica.)

## macOS

Nada que hacer: el daemon ya tiene `KeepAlive=true` (se reinicia solo) y
`RunAtLoad=true` (arranca en el boot).

## Nota

Todo esto es el **servicio**, no la ventana. Si un usuario cierra la ventana de
Fontis Remote, el acceso remoto sigue disponible. El tray se autoarranca en el
login (acceso directo en la carpeta Inicio); si lo quitan, el servicio sigue
igual. Para impedir que el usuario desactive el servicio hace falta bloquear
ajustes por directiva; consultar si se necesita.
