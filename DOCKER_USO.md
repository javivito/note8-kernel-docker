# Docker en Samsung Note 8 — Guía de uso

> **Setup ya instalado en este dispositivo.** Esta guía documenta cómo está configurado
> y cómo usarlo. Si partes de cero, consulta primero `KERNEL_DOCKER_GUIDE.md`.

## Qué hay instalado

| Fichero | Ubicación en dispositivo | Para qué |
|---|---|---|
| `start_docker_note8.sh` | `/sdcard/Download/start_docker_note8.sh` | Arranca dockerd con cgroupv1 y storage driver vfs |
| `daemon.json` | `/data/data/com.termux/files/usr/etc/docker/daemon.json` | Config de dockerd (vfs, sin iptables ni bridge) |
| `magisk_service_docker.sh` | `/data/adb/service.d/termux_path.sh` | Arranque automático + docker para root + ADB WiFi |
| `docker_xbin` | `/data/adb/docker_xbin` | Wrapper docker usado por el service.d |
| Wrapper Termux | `/data/data/com.termux/files/usr/bin/docker` | Inyecta DOCKER_HOST para usuario Termux |
| Log arranque | `/data/adb/boot.log` | Diagnóstico del arranque automático |
| Log dockerd | `/sdcard/Download/dockerd.log` | Log del daemon de Docker |

---

## 1. Arrancar Docker

### Automático (si Termux:Boot está instalado)

No hace falta hacer nada. Al encender el móvil, Termux:Boot ejecuta
`~/.termux/boot/start_docker.sh` que espera 30 segundos y lanza Docker solo.

### Manual (desde Termux)

```sh
su -c 'sh /sdcard/Download/start_docker_note8.sh'
```

Espera ~20 segundos hasta ver "Docker is up!".

---

## 2. Usar Docker

Abrir Termux, escribir `su` y ya:

```sh
su
docker ps
docker images
docker run --rm --net=host alpine echo OK
```

No hace falta escribir nada más — el módulo Magisk y el wrapper inyectan
el PATH y el socket automáticamente.

---

## 3. Lanzar un contenedor

### Ejemplo básico

```sh
su
docker run --rm --net=host alpine echo OK
```

### Portainer (panel web de Docker)

```sh
su
docker run -d \
  --name portainer \
  --net=host \
  --restart=unless-stopped \
  -v /data/data/com.termux/files/usr/var/run/docker.sock:/var/run/docker.sock \
  -v portainer_data:/data \
  portainer/portainer-ce:latest
```

Acceder en `http://<ip-del-movil>:9000`

### Nextcloud con MariaDB (5 usuarios, compose para Portainer → Stacks)

```yaml
services:
  db:
    image: mariadb:10.11
    restart: unless-stopped
    network_mode: host
    environment:
      - MYSQL_ROOT_PASSWORD=rootpassword
      - MYSQL_DATABASE=nextcloud
      - MYSQL_USER=nextcloud
      - MYSQL_PASSWORD=nextcloudpassword
    volumes:
      - /data/nextcloud_db:/var/lib/mysql

  nextcloud:
    image: nextcloud:latest
    restart: unless-stopped
    network_mode: host
    depends_on:
      - db
    environment:
      - MYSQL_HOST=127.0.0.1
      - MYSQL_DATABASE=nextcloud
      - MYSQL_USER=nextcloud
      - MYSQL_PASSWORD=nextcloudpassword
      - NEXTCLOUD_ADMIN_USER=admin
      - NEXTCLOUD_ADMIN_PASSWORD=tupassword
      - NEXTCLOUD_TRUSTED_DOMAINS=192.168.1.191
    volumes:
      - /data/nextcloud:/var/www/html
```

> Con storage driver `vfs` no hace falta `privileged` ni `cap_add`.
> Cambiar `192.168.1.191` por la IP de tu dispositivo.
> Acceder en `http://<ip>:80`

> **Nota sobre el socket:** Las apps que _gestionan_ Docker (Portainer, Watchtower, Traefik)
> necesitan montar el socket con `-v`. La ruta en este dispositivo es siempre:
> `/data/data/com.termux/files/usr/var/run/docker.sock`
> Las apps normales (Nextcloud, Jellyfin, etc.) no necesitan el socket.

### Redes disponibles

- `--net=host` — comparte la red del móvil ✅
- `--net=none` — sin red ✅
- `--net=bridge` — NO funciona (iptables y bridge desactivados en daemon.json)

---

## 4. Si Docker no responde

```sh
# Ver si el daemon corre
su -c 'ps aux | grep dockerd'

# Reiniciar
su -c 'killall dockerd containerd 2>/dev/null; sh /sdcard/Download/start_docker_note8.sh'
```

Log del daemon: `/sdcard/Download/dockerd.log`

---

## 5. Instalar el setup en otro dispositivo (paso a paso)

> Requisito previo: kernel custom con Docker habilitado ya flasheado. Ver `KERNEL_DOCKER_GUIDE.md`.
> El móvil debe tener **Magisk** instalado (root) y **Termux** instalado desde F-Droid.

---

### Paso 1 — Instalar docker en Termux

Abre Termux en el móvil y escribe:

```sh
pkg update
pkg install docker
```

Cuando termine, cierra Termux.

---

### Paso 2 — Crear el daemon.json

Esto configura Docker para Android: sin iptables ni bridge (no funcionan), y usando
el storage driver `vfs` en lugar de `overlay2`.

> **¿Por qué vfs?** El kernel 4.4 de Samsung tiene limitaciones con overlay2 que impiden
> que procesos dentro de los contenedores lean ficheros de la imagen (rsync falla con
> "Operation not permitted"). `vfs` es más simple y no tiene esas limitaciones.
> El inconveniente es que usa más espacio en disco (~2-3x más que overlay2).

En Termux (la ruta correcta en Termux es distinta a Linux normal):

```sh
su
mkdir -p /data/data/com.termux/files/usr/etc/docker
cat > /data/data/com.termux/files/usr/etc/docker/daemon.json << 'EOF'
{
    "data-root": "/data/data/com.termux/files/usr/lib/docker",
    "exec-root": "/data/data/com.termux/files/usr/var/run/docker",
    "pidfile": "/data/data/com.termux/files/usr/var/run/docker.pid",
    "hosts": ["unix:///data/data/com.termux/files/usr/var/run/docker.sock"],
    "storage-driver": "vfs",
    "iptables": false,
    "ip-masq": false,
    "bridge": "none"
}
EOF
exit
```

---

### Paso 3 — Copiar los scripts al móvil

Descarga desde el repositorio estos tres ficheros y ponlos en `/sdcard/Download/`:

- `start_docker_note8.sh` — arranca Docker
- `docker_xbin` — wrapper para root (es el fichero `docker_wrapper.sh` renombrado)
- `magisk_service_docker.sh` — script de arranque de Magisk

Puedes hacerlo conectando el móvil al PC por USB y copiando directamente a la carpeta
Descargas, o usando ADB:

```sh
adb push start_docker_note8.sh /sdcard/Download/start_docker_note8.sh
adb push docker_wrapper.sh /sdcard/Download/docker_xbin
adb push magisk_service_docker.sh /sdcard/Download/magisk_service_docker.sh
```

---

### Paso 4 — Instalar el wrapper en Termux

Esto hace que puedas escribir `docker` en Termux sin poner variables de entorno.

**Abre Termux** en el móvil (importante: no como root, abrir Termux normal) y escribe:

```sh
mv /data/data/com.termux/files/usr/bin/docker \
   /data/data/com.termux/files/usr/bin/docker.real

cp /sdcard/Download/docker_xbin \
   /data/data/com.termux/files/usr/bin/docker

chmod +x /data/data/com.termux/files/usr/bin/docker
```

> **Por qué desde Termux y no desde root:** Los ficheros dentro de la carpeta de Termux
> necesitan pertenecer al usuario de Termux. Si los creas como root (con `su`) Android
> les pone un identificador de seguridad incorrecto y Termux no puede usarlos,
> aunque el permiso sea correcto.

---

### Paso 5 — Instalar el script de Magisk (arranque automático + docker para root)

Este script hace tres cosas en cada arranque:
1. Pone `docker` disponible para root sin escribir PATH
2. Activa ADB por WiFi en el puerto 5555
3. Arranca Docker automáticamente

> **Importante:** Los ficheros en `/data/adb/` tienen un contexto de seguridad especial
> (`adb_data_file`) que solo puede escribirse desde el proceso `magiskd`, no desde un
> `su` normal de ADB. Por eso hay que usar `nsenter` para entrar en el espacio de
> nombres de Magisk antes de copiar el fichero.

Conecta el móvil por USB al PC y ejecuta desde el PC:

```sh
# 1. Ver el PID de magiskd
adb shell su -c 'ps -A | grep magiskd'
# Apunta el primer PID que aparezca (el de /1 como padre)

# 2. Abrir shell en el namespace de magiskd (sustituye <PID> por el número)
adb shell su -c 'nsenter --mount=/proc/<PID>/ns/mnt -- /system/bin/sh'
```

Ahora estás dentro del namespace correcto. Copia los ficheros:

```sh
# Copiar el script de arranque
cp /sdcard/Download/magisk_service_docker.sh /data/adb/service.d/termux_path.sh
chmod +x /data/adb/service.d/termux_path.sh

# Copiar el wrapper de docker para root
cp /sdcard/Download/docker_xbin /data/adb/docker_xbin
chmod +x /data/adb/docker_xbin

# Salir del namespace
exit
```

> **Rutas:** Las rutas `/data/adb/` son las mismas en todos los dispositivos Android con Magisk.
> No necesitas cambiarlas.

> **¿Por qué nsenter?** `adb shell su -c` da root pero con el contexto SELinux de ADB (`shell`),
> que no puede escribir en `/data/adb/`. `nsenter` entra en el contexto real de Magisk
> que sí tiene permiso.

---

### Paso 6 — Reiniciar y verificar

Reinicia el móvil. Espera **~2 minutos** (el script espera 45 segundos a que el sistema
arranque, luego otros 20-25 segundos para que Docker esté listo).

Desde el PC con ADB:
```sh
# Conectar por WiFi (ya no necesitas USB)
adb connect <IP_del_movil>:5555

# Probar docker
adb shell su -c 'docker ps'
```

O desde Termux en el móvil:
```sh
su
docker ps
```

Si ves una tabla (aunque esté vacía) todo funciona.

Si falla, comprueba el log de arranque:
```sh
su -c 'cat /data/adb/boot.log'
```

Y el log de dockerd:
```sh
cat /sdcard/Download/dockerd.log | tail -20
```

Si el arranque automático falla, puedes arrancarlo manualmente:
```sh
su -c 'sh /sdcard/Download/start_docker_note8.sh'
```

---

## Fallos conocidos y soluciones

### `bpf_prog_query failed: invalid argument`
Samsung LSM bloquea BPF. El kernel custom tiene stubs que lo evitan, y el script
de arranque usa cgroupv1 con `unshare -m` para que Docker no necesite BPF.

### Kernel panic con `--net=host`
Fix en `ipc/namespace.c`: `ns->user_ns = get_user_ns()` debe ir ANTES de `mq_init_ns(ns)`.

### Contenedor arranca con rootfs vacío
- Pull interrumpido: `docker rmi <imagen> && docker pull --platform linux/arm64 <imagen>`
- Archivo `link` vacío en overlay2: `printf 'SHORTID' > overlay2/<id>/link`

### `exec format error`
Imagen descargada era amd64. Usar siempre `--platform linux/arm64`.

### WiFi se duerme con ADB
`adb shell svc wifi enable`
