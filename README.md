# Docker en Samsung Note 8 (greatlte) — LineageOS 19.1

Kernel custom 4.4.302 para Samsung Galaxy Note 8 (SM-N950F, Exynos 8895)
con soporte Docker completo y Samsung LSM desactivado.

## Dispositivo de referencia

| Campo | Valor |
|---|---|
| Modelo | Samsung Galaxy Note 8 SM-N950F |
| Codename | greatlte / greatltexx |
| SoC | Exynos 8895 (aarch64) |
| ROM | LineageOS 19.1 (Android 12) |
| Root | Magisk |
| Kernel | 4.4.302 custom (este repo) |

---

## Qué incluye este kernel

### Docker habilitado
- `CONFIG_OVERLAY_FS=y` — storage driver overlay2
- `CONFIG_BRIDGE=y`, `CONFIG_BRIDGE_NETFILTER=y` — redes
- `CONFIG_VETH=y`, `CONFIG_NET_NS=y` — ya presentes en defconfig

### Samsung LSM desactivado
El kernel stock de Samsung incluye módulos de seguridad que bloquean Docker:

| Módulo | Qué hace | Por qué lo desactivamos |
|---|---|---|
| DEFEX | Bloquea ejecución de binarios no firmados | Impide que dockerd ejecute procesos dentro de contenedores |
| TIMA | TrustZone Integrity Management | Interfiere con namespaces y cgroups |
| Knox KAP/NCM | Knox Always-on Protection | Bloquea escritura en áreas del kernel |
| DSMS | Samsung Messaging System | Innecesario sin Knox |

Con estos módulos desactivados Docker funciona como en una Raspberry Pi:
- Storage driver `overlay2` (no hace falta `vfs`)
- `rsync` y otros binarios dentro de contenedores funcionan sin errores
- No hace falta `--privileged` ni `--cap-add` extra

### Parches aplicados
- **ipc/namespace.c**: mueve `ns->user_ns = get_user_ns()` ANTES de `mq_init_ns()` → fix kernel panic con `docker run --net=host`
- **kernel/bpf/syscall.c**: stubs BPF para evitar el bloqueo de Samsung LSM:
  - `BPF_PROG_QUERY` → ENOENT
  - `BPF_PROG_LOAD` tipo `CGROUP_DEVICE` → fd anónimo
  - `BPF_PROG_ATTACH/DETACH` tipo `BPF_CGROUP_DEVICE` → 0

---

## Fichero del kernel

```
note8-greatlte-lineageos19.1-4.4.302-docker-nolsm.Image
```

Es el kernel ARM64 en formato **raw (sin comprimir)**, listo para flashear con magiskboot.
El bootloader de greatlte requiere formato raw. NO usar Image.gz ni Image.gz-dtb directamente.

---

## 1. Flashear el kernel

> Requisitos: Magisk instalado, LineageOS 19.1, ADB habilitado.

### Opción A — Desde el PC por ADB (dispositivo encendido)

```sh
# Subir el kernel
adb push note8-greatlte-lineageos19.1-4.4.302-docker-nolsm.Image /sdcard/Download/Image

# Flashear (ejecutar como root en el dispositivo)
adb shell su -c 'sh /sdcard/Download/flash_kernel.sh'
```

Crea `/sdcard/Download/flash_kernel.sh` con este contenido:

```sh
#!/system/bin/sh
BOOT=/dev/block/platform/11120000.ufs/by-name/BOOT
MAGISKBOOT=/data/adb/magisk/magiskboot
WORKDIR=/sdcard/Download/kernel_flash
mkdir -p $WORKDIR
cd $WORKDIR
$MAGISKBOOT unpack $BOOT
cp /sdcard/Download/Image kernel
$MAGISKBOOT repack $BOOT new-boot.img
dd if=new-boot.img of=$BOOT
echo "FLASH DONE"
```

```sh
adb push flash_kernel.sh /sdcard/Download/flash_kernel.sh
adb shell su -c 'sh /sdcard/Download/flash_kernel.sh'
adb reboot
```

### Opción B — Desde recovery (TWRP)

Si el dispositivo está en recovery (o en boot loop):

```sh
adb push note8-greatlte-lineageos19.1-4.4.302-docker-nolsm.Image /sdcard/Download/Image
adb shell 'sh /sdcard/Download/flash_kernel.sh'
adb reboot
```

> **Nota de rutas:** `/dev/block/platform/11120000.ufs/by-name/BOOT` y
> `/data/adb/magisk/magiskboot` son rutas específicas de este dispositivo.
> En otros dispositivos Samsung pueden variar. Busca con:
> `ls /dev/block/platform/*/by-name/BOOT`

---

## 2. Instalar Docker

### Paso 1 — Instalar docker en Termux

```sh
pkg update
pkg install docker
```

### Paso 2 — Crear daemon.json

En Termux (como root):

```sh
su
mkdir -p /data/data/com.termux/files/usr/etc/docker
cat > /data/data/com.termux/files/usr/etc/docker/daemon.json << 'CONF'
{
    "data-root": "/data/data/com.termux/files/usr/lib/docker",
    "exec-root": "/data/data/com.termux/files/usr/var/run/docker",
    "pidfile": "/data/data/com.termux/files/usr/var/run/docker.pid",
    "hosts": ["unix:///data/data/com.termux/files/usr/var/run/docker.sock"],
    "storage-driver": "overlay2",
    "iptables": false,
    "ip-masq": false,
    "bridge": "none"
}
CONF
exit
```

> Las rutas `/data/data/com.termux/files/usr/` son específicas de Termux.
> En Linux normal serían `/etc/docker/` y `/var/run/docker/`.

### Paso 3 — Copiar los scripts al móvil

Descarga del repositorio y copia a `/sdcard/Download/`:

```sh
adb push start_docker_note8.sh /sdcard/Download/start_docker_note8.sh
adb push docker_wrapper.sh /sdcard/Download/docker_xbin
adb push magisk_service_docker.sh /sdcard/Download/magisk_service_docker.sh
```

### Paso 4 — Instalar el wrapper en Termux

**Desde Termux** (NO como root — los ficheros deben pertenecer al usuario de Termux):

```sh
TBIN=/data/data/com.termux/files/usr/bin
mv $TBIN/docker $TBIN/docker.real
cp /sdcard/Download/docker_xbin $TBIN/docker
chmod +x $TBIN/docker
```

### Paso 5 — Instalar arranque automático con Magisk

Los ficheros en `/data/adb/` requieren el contexto SELinux de magiskd.
Hay que usar `nsenter` para entrar en ese namespace:

```sh
# Obtener el PID de magiskd
adb shell su -c 'ps -A | grep magiskd'
# Apunta el primer PID (con /1 como padre)

# Entrar en el namespace de magiskd (sustituye <PID>)
adb shell su -c 'nsenter --mount=/proc/<PID>/ns/mnt -- /system/bin/sh'
```

Dentro del namespace:

```sh
cp /sdcard/Download/magisk_service_docker.sh /data/adb/service.d/termux_path.sh
chmod +x /data/adb/service.d/termux_path.sh
cp /sdcard/Download/docker_xbin /data/adb/docker_xbin
chmod +x /data/adb/docker_xbin
exit
```

### Paso 6 — Reiniciar y verificar

Reinicia el móvil. Docker arranca automáticamente en ~2 minutos.

```sh
adb connect <IP_del_movil>:5555

# Verificar
adb shell su -c 'cat /data/adb/boot.log'
```

Desde Termux en el móvil:
```sh
su
docker ps
```

---

## 3. Usar Docker

```sh
su
docker ps
docker images
docker run --rm --net=host alpine echo OK
```

No hace falta escribir DOCKER_HOST ni PATH — el wrapper lo inyecta automáticamente.

### Redes disponibles

- `--net=host` — comparte la red del móvil ✅
- `--net=none` — sin red ✅
- `--net=bridge` — NO funciona (iptables y bridge desactivados en daemon.json)

---

## 4. Lanzar contenedores

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

> Solo las apps que gestionan Docker (Portainer, Watchtower) necesitan montar el socket.
> La ruta del socket en este dispositivo es siempre:
> `/data/data/com.termux/files/usr/var/run/docker.sock`

### Nextcloud con MariaDB (via Portainer → Stacks)

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

> Cambia `192.168.1.191` por la IP de tu dispositivo.
> Acceder en `http://<ip>:80`

---

## 5. Si Docker no responde

```sh
# Ver si el daemon corre
su -c 'ps aux | grep dockerd'

# Log del daemon
cat /sdcard/Download/dockerd.log | tail -20

# Reiniciar manualmente
su -c 'killall dockerd containerd 2>/dev/null; sh /sdcard/Download/start_docker_note8.sh'
```

---

## Cómo funciona el arranque automático

1. Magisk ejecuta `/data/adb/service.d/termux_path.sh` como root (~45s tras encender):
   - Copia el wrapper `docker` a `/debug_ramdisk/` (tmpfs en el PATH de root)
   - Activa ADB WiFi en el puerto 5555
   - Arranca dockerd con `unshare -m` + cgroupv1
2. Docker listo ~2 minutos tras encender el móvil

---

## Compilar el kernel

El kernel se compila automáticamente en GitHub Actions con cada push.

- **Fuente**: `https://github.com/8890q/android_kernel_samsung_universal8895` rama `lineage-19.1`
- **Defconfig**: `exynos8895-greatlte_defconfig`
- **Compilador**: gcc-9 aarch64-linux-gnu (ubuntu-22.04)
- **Patches**: ver carpeta `patches/`
- **Workflow**: `.github/workflows/build.yml`
- **Artefactos**: `Image` (raw, flasheable) + zip AnyKernel3

---

## Fallos conocidos

### `bpf_prog_query failed: invalid argument`
Samsung LSM bloquea BPF. El kernel tiene stubs que lo evitan, y el script
de arranque usa cgroupv1 con `unshare -m`.

### Kernel panic con `--net=host`
Fix en `ipc/namespace.c`: `ns->user_ns = get_user_ns()` debe ir ANTES de `mq_init_ns(ns)`.

### Boot loop tras flashear
- Causa más común: usar `Image.gz-dtb` en vez de `Image` (raw). El bootloader de greatlte
  necesita el kernel sin comprimir.
- Recuperar desde recovery: extraer boot actual, reconstruir con kernel correcto, reflashear.

### WiFi se duerme con ADB
`adb shell svc wifi enable`
