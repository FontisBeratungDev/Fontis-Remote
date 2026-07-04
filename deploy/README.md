# Despliegue de la libreta central (rustdesk-api)

Servidor API community ([lejianwen/rustdesk-api](https://github.com/lejianwen/rustdesk-api))
que añade a la instalación OSS: **login de usuarios en el cliente, libreta de
direcciones centralizada, grupos/etiquetas, consola web de administración,
registro de conexiones y un cliente web integrado** servido desde vuestro dominio.

## Pasos

1. Copiar `docker-compose.yml` al servidor. Si hbbs/hbbr ya corren fuera de
   este compose, levantar solo la API:

   ```bash
   docker compose up -d rustdesk-api
   ```

2. Abrir el puerto **TCP 21114** en el firewall del servidor (hoy está cerrado).

3. Primer arranque: la consola queda en `http://rustdesk.fontisberatung.ch:21114/_admin/`.
   Las credenciales iniciales del admin se imprimen en los logs:

   ```bash
   docker logs rustdesk-api | head -50
   ```

   Cambiar la contraseña del admin de inmediato desde la consola.

4. Crear los usuarios del equipo (o conectar OAuth/LDAP si se quiere más adelante).

5. **Cliente web propio**: la API sirve un cliente web en
   `http://rustdesk.fontisberatung.ch:21114/webclient/` — acceso por navegador
   contra vuestro servidor, sin depender de web.rustdesk.com.

6. Avisar a Claude para re-compilar el cliente con la API embebida:
   `API_SERVER=http://rustdesk.fontisberatung.ch:21114` en `branding/branding.env`
   → los clientes traen el botón de login y la libreta configurados de fábrica
   (release `1.4.8-4`).

## TLS con el wildcard *.fontisberatung.ch (recomendado desde el inicio)

Ya existe el certificado wildcard de Sectigo (carpeta `STAR.fontisberatung.ch_cert`,
válido hasta dic-2026). Configuración lista en [nginx-rustdesk.conf](nginx-rustdesk.conf):

- Consola: `https://rustdesk.fontisberatung.ch/_admin/`
- Cliente web propio: `https://rustdesk.fontisberatung.ch/webclient/`
- Websockets `wss://` en `/ws/id` y `/ws/relay` (evita el bloqueo por contenido
  mixto del navegador; con esto 21114/21118/21119 pueden cerrarse al exterior
  y dejar solo 443).
- `API_SERVER` embebido en el cliente: `https://rustdesk.fontisberatung.ch`

Sin TLS, las contraseñas de login del cliente viajan por HTTP plano — con el
wildcard disponible no hay motivo para saltarse este paso.

## Backup

- `./data/hbbs` (claves del servidor — **crítico**: si se pierden, todos los
  clientes desplegados quedan huérfanos) y `./data/api` (usuarios/libreta).

## Verificación rápida

```bash
curl http://rustdesk.fontisberatung.ch:21114/api/login-options   # debe devolver JSON
```
