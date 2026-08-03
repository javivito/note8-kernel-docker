# Cómo usar Docker en el Note 8

## Requisitos previos
- Kernel 4.4.302 custom flasheado (con BPF stubs + IPC fix)
- Termux con paquete `docker` instalado
- `/etc/docker/daemon.json` con `iptables:false, bridge:none`
- Script `/sdcard/Download/start_docker_note8.sh` en el dispositivo

## 1. Arrancar Docker (tras cada reboot)

Desde Termux:
```sh
su -c 'sh /sdcard/Download/start_docker_note8.sh'
```
Espera ~20 segundos hasta que aparezca "Docker is up!".

O desde PC con ADB:
```sh
adb shell "su -c 'sh /sdcard/Download/start_docker_note8.sh'"
```

## 2. Usar Docker desde Termux (forma recomendada)

Abrir shell root y trabajar desde ahí:
```sh
su
export DOCKER_HOST=unix:///data/data/com.termux/files/usr/var/run/docker.sock
docker ps
docker images
docker run --rm alpine echo OK
docker run --rm --net=host alpine sh
```

### Configurar para no escribir DOCKER_HOST siempre

Ejecuta esto una sola vez (como root en Termux):
```sh
echo 'export DOCKER_HOST=unix:///data/data/com.termux/files/usr/var/run/docker.sock' \
  >> /data/data/com.termux/files/usr/etc/bash.bashrc
```

Así cada `su` en Termux ya tiene docker listo sin escribir nada más.

## 3. Usar Docker desde PC vía ADB
```sh
adb shell "su -c 'PATH=/data/data/com.termux/files/usr/bin:/system/xbin:/system/bin \
  DOCKER_HOST=unix:///data/data/com.termux/files/usr/var/run/docker.sock \
  docker run --rm alpine echo OK'"
```

## 4. Configurar para no escribir DOCKER_HOST siempre

Ver sección 2 — el bashrc trick aplica igual.

## Notas importantes

- `--net=host`: comparte red del dispositivo (funciona)
- `--net=none`: sin red (funciona)
- `--net=bridge`: NO funciona (iptables desactivado, bridge desactivado)
- Las imágenes se guardan en `/data/data/com.termux/files/usr/lib/docker`
- Log del daemon: `/sdcard/Download/dockerd.log`

## Si Docker no responde tras reboot

```sh
# Ver si el daemon está corriendo
su -c 'ps aux | grep dockerd'

# Reiniciar
su -c 'killall dockerd containerd 2>/dev/null; sh /sdcard/Download/start_docker_note8.sh'
```

## Ejemplo: contenedor Debian con shell
```sh
su
export DOCKER_HOST=unix:///data/data/com.termux/files/usr/var/run/docker.sock
docker pull --platform linux/arm64 debian:bookworm-slim
docker run --rm -it --net=host debian:bookworm-slim bash
```

---

## Fallos encontrados y soluciones

### 1. `bpf_prog_query failed: invalid argument`
- **Causa**: Samsung LSM bloquea TODOS los comandos BPF con EINVAL antes del switch del kernel
- **Síntoma**: Docker detecta cgroupv2, intenta usar BPF device manager, falla al arrancar contenedor
- **Solución A (kernel)**: Añadir stubs BPF en `SYSCALL_DEFINE3(bpf,...)` antes del `security_bpf()`:
  - cmd=12 → ENOENT (query: "sin programas")
  - cmd=5 + prog_type=15 → anon_inode fd (stub prog load)
  - cmd=8/9 + attach_type=7 → 0 (stub attach/detach)
- **Solución B (cgroupv1)**: Arrancar dockerd en namespace con cgroupv1 (`unshare -m`) → Docker no usa BPF

### 2. Kernel panic con `docker run --net=host`
- **Causa**: `create_ipc_ns()` llama `mq_init_ns(ns)` antes de inicializar `ns->user_ns` → NULL pointer
- **Solución**: En `ipc/namespace.c`, mover `ns->user_ns = get_user_ns(user_ns)` ANTES de `mq_init_ns(ns)` (y añadir `put_user_ns` en el error path)

### 3. Contenedor arranca con rootfs vacío (`stat /bin/sh: no such file or directory`)
- **Causa A**: Archivo `link` del layer de imagen vacío → overlay no puede construir el lower path
  - Fix: `printf 'SHORTID' > overlay2/<layerid>/link` (ver ID en `overlay2/l/`)
- **Causa B**: Docker usado con `--containerd=<socket-externo>` → usa el snapshotter de ese containerd (vacío)
  - Fix: NO usar `--containerd`, dejar que dockerd gestione su propio containerd
- **Causa C**: Pull de imagen interrumpido → binarios vacíos
  - Fix: `docker rmi alpine && docker pull --platform linux/arm64 alpine`

### 4. `exec format error` al ejecutar binario en contenedor
- **Causa**: Imagen descargada era amd64 en vez de arm64
- **Fix**: `docker pull --platform linux/arm64 <imagen>`

### 5. `failed to start containerd: timeout waiting for containerd to start`
- **Causa**: Containerd tarda >14s en arrancar; dockerd timeout demasiado corto
- **Fix**: No usar `--containerd` externo; dejar que dockerd lo gestione (arranca en background y espera más)

### 6. overlay2 `failed to mount overlay: no space left on device`
- **Causa**: Incompatibilidad de opciones overlay2 entre Debian Docker 26.1.5 y kernel 4.4
- **Fix**: Usar el dockerd de Termux (versión compatible), no el de Debian chroot

### 7. `runc: executable file not found in $PATH`
- **Causa**: dockerd/containerd arrancados sin el PATH de Termux
- **Fix**: Exportar `PATH=/data/data/com.termux/files/usr/bin:/system/xbin:/system/bin` antes de dockerd

### 8. `pivot_root` falla / contenedor no arranca en Debian chroot
- **Causa**: Sin namespace de mount propio, pivot_root falla
- **Fix**: Usar `unshare --mount` antes de dockerd

### 9. WiFi se duerme, ADB pierde conexión
- **Causa**: Android apaga WiFi por ahorro energía
- **Fix**: `adb shell svc wifi enable` o conectar el cargador
