# Docker en Samsung Note 8 — Guía de uso

> **Setup ya instalado en este dispositivo.** Esta guía documenta cómo está configurado
> y cómo usarlo. Si partes de cero, consulta primero `KERNEL_DOCKER_GUIDE.md`.

## Qué hay instalado

| Fichero | Ubicación | Para qué |
|---|---|---|
| Script arranque Docker | `/sdcard/Download/start_docker_note8.sh` | Arranca dockerd con cgroupv1 |
| Arranque automático | `~/.termux/boot/start_docker.sh` | Lo lanza solo al encender el móvil |
| Wrapper Termux | `/data/data/com.termux/files/usr/bin/docker` | Inyecta el socket, evita escribir DOCKER_HOST |
| Script Magisk service.d | `/data/adb/service.d/termux_path.sh` | Pone `docker` en `/debug_ramdisk` para root en cada boot |

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

## 5. Instalar el setup en otro dispositivo

Si quieres replicar esto en otro móvil necesitas:

1. **Kernel compatible** con Docker (BPF stubs + IPC fix) — ver `KERNEL_DOCKER_GUIDE.md`
2. **Termux** con `docker` instalado: `pkg install docker`
3. **daemon.json** en `/etc/docker/daemon.json`:
   ```json
   {"iptables": false, "ip-masq": false, "bridge": "none"}
   ```
4. **Script de arranque** — copiar `start_docker_note8.sh` a `/sdcard/Download/`
5. **Wrapper Termux** — ejecutar esto _desde dentro de Termux_ (no desde ADB/root):
   ```sh
   TBIN=/data/data/com.termux/files/usr/bin
   mv $TBIN/docker $TBIN/docker.real
   cp docker_wrapper.sh $TBIN/docker
   chmod +x $TBIN/docker
   ```
   > Los ficheros de Termux necesitan el UID de Termux. Si los creas como root desde ADB
   > quedan con contexto SELinux incorrecto y Termux no puede ejecutarlos.

6. **Script Magisk service.d** — copiar `magisk_service_docker.sh` a `/data/adb/service.d/termux_path.sh`
   y hacerlo ejecutable. En cada boot copia el wrapper a `/debug_ramdisk/` (que está en el PATH de root).
   También copiar `docker_xbin` a `/sdcard/Download/docker_xbin` en el dispositivo.

7. **Termux:Boot** (opcional) — instalar desde F-Droid, abrirlo una vez, y ejecutar
   _desde Termux_:
   ```sh
   mkdir -p ~/.termux/boot
   cp termux_boot_start_docker.sh ~/.termux/boot/start_docker.sh
   chmod +x ~/.termux/boot/start_docker.sh
   ```
   > Igual que el wrapper: crear siempre desde Termux, nunca como root externo.

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
