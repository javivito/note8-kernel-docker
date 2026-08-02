# Docker en Android — Guía Completa (Note 8 / greatlte)

## Dispositivo de referencia
- Samsung Galaxy Note 8 SM-N950F (greatltexx, Exynos 8895, aarch64)
- ROM: LineageOS 20 (Android 13) by ivanmeler
- Magisk 27.0 (root)
- Kernel: 4.4.302-g76ccdeff (custom compilado con soporte Docker)

---

## PARTE 1 — Compilar el kernel con soporte Docker

### Repositorio de compilación
- GitHub: https://github.com/javivito/note8-kernel-docker
- Workflow: `.github/workflows/build.yml`
- Backup boot partition listo para flashear: en la pestaña Releases del repo

### Fuente del kernel correcta
```
Repo:   https://github.com/8890q/android_kernel_samsung_universal8895
Rama:   lineage-19.1
Kernel: 4.4.302 (mismo que el dispositivo — 8890q = ivanmeler)
```
**NO usar** `ivanmeler/android_kernel_samsung_universal8895 seals-pie-new` (es 4.4.111, incompatible con LineageOS 20).

### Opciones Docker a añadir (docker.fragment)
```
CONFIG_BRIDGE=y
CONFIG_BRIDGE_NETFILTER=y
CONFIG_OVERLAY_FS=y
```
(CONFIG_VETH y CONFIG_NET_NS ya están en el defconfig)

### Compilación (GitHub Actions, ubuntu-22.04, gcc-9)
```yaml
- git clone --depth=1 --branch lineage-19.1 \
    https://github.com/8890q/android_kernel_samsung_universal8895 kernel
- cd kernel && make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- exynos8895-greatlte_defconfig
- cat docker.fragment >> .config
- [añadir CONFIG_RKP=n ... CONFIG_TIMA_LOG=n]
- make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- olddefconfig
- make -j$(nproc) ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- \
    HOSTCFLAGS="-fcommon" KCFLAGS="-Wno-error" Image.gz-dtb
```

### ⚠️ CRÍTICO: Formato del kernel para greatlte

El bootloader de greatlte espera **ARM64 Image RAW (sin comprimir)**.
El build genera `Image.gz-dtb` (gzip) → hay que descomprimirlo:

```bash
gunzip -c Image.gz-dtb > Image-raw
# El warning "trailing garbage ignored" es normal (son los DTBs al final)
```

Verificar formato correcto (debe empezar por `10 00 00 14`, NO por `1f 8b`):
```bash
xxd Image-raw | head -1
```

### Flashear con magiskboot
```bash
# 1. Subir Image-raw al dispositivo
adb push Image-raw /sdcard/Download/Image-raw

# 2. En el dispositivo (root):
cd /data/local/tmp
/data/adb/magisk/magiskboot unpack /sdcard/Download/boot_backup_lineage20.img
cp /sdcard/Download/Image-raw kernel
/data/adb/magisk/magiskboot repack /sdcard/Download/boot_backup_lineage20.img /sdcard/Download/new-boot.img

# 3. Flashear la partición BOOT de greatlte:
dd if=/sdcard/Download/new-boot.img \
   of=/dev/block/platform/11120000.ufs/by-name/BOOT bs=4096
sync
```

### Verificar tras reiniciar
```bash
adb shell su -c "cat /proc/config.gz | gunzip | grep -E 'CONFIG_BRIDGE=|CONFIG_OVERLAY_FS=|CONFIG_VETH=|CONFIG_NET_NS='"
# Resultado esperado:
# CONFIG_BRIDGE=y
# CONFIG_NET_NS=y
# CONFIG_OVERLAY_FS=y
# CONFIG_VETH=y
```

---

## PARTE 2 — Instalar Docker en Termux (desde root-repo)

Docker en Termux es la mejor opción: los paquetes están parchados para Android
(fix cpuset noprefix, fix mqueue, etc.)

```bash
# En Termux:
pkg install root-repo
pkg install dockerd docker-cli
```

---

## PARTE 3 — Script de arranque de Docker

Guardar como `~/bin/startdocker` en Termux:

```bash
#!/data/data/com.termux/files/usr/bin/bash

PREFIX="/data/data/com.termux/files/usr"
export PATH="$PREFIX/bin:/system/xbin:/system/bin:$PATH"

# Desmontar mqueue para evitar conflicto con Android
# (CRÍTICO: sin esto el contenedor falla con "device or resource busy")
umount /dev/mqueue 2>/dev/null || true

# Matar instancias previas
pkill -f dockerd 2>/dev/null
pkill -f containerd 2>/dev/null
sleep 1

# Arrancar Docker daemon
dockerd --iptables=false \
        --log-level=warn \
        > /sdcard/Download/dockerd.log 2>&1 &

echo "Docker daemon iniciando... (espera 10s)"
sleep 10

# Verificar
if docker info > /dev/null 2>&1; then
    echo "✓ Docker listo"
    docker version --format 'Client: {{.Client.Version}} / Server: {{.Server.Version}}'
else
    echo "✗ Error arrancando Docker. Log:"
    tail -5 /sdcard/Download/dockerd.log
fi
```

```bash
chmod +x ~/bin/startdocker
```

---

## PARTE 4 — Usar Docker

### Ejecutar siempre como root (su -c o tsu)
```bash
# Arrancar daemon:
su -c "startdocker"

# Correr contenedor (--net=host necesario en Android):
su -c "docker run --rm --net=host --dns=8.8.8.8 alpine echo hola"

# Contenedor interactivo:
su -c "docker run -it --rm --net=host --dns=8.8.8.8 alpine sh"

# Contenedor con volumen:
su -c "docker run --rm --net=host --dns=8.8.8.8 -v /sdcard/datos:/data alpine sh"
```

### ⚠️ NO usar --privileged
El flag `--privileged` da acceso a `/dev/video*` lo que causa un **kernel panic**
por el bug del driver de cámara Samsung (`fimc_is_ixs_video_querycap` NULL pointer).

Si necesitas privilegios específicos, usar `--cap-add` individual:
```bash
docker run --cap-add NET_ADMIN --cap-add SYS_ADMIN ...
```

---

## PARTE 5 — Solución de problemas

### Error: `failed to register layer: remount /, flags: 0x84000: invalid argument`
- **Causa**: El directorio del chroot no es un mount point real para el kernel.
  `MS_SLAVE|MS_REC` falla porque el proceso de extracción de capas necesita
  que `/` sea la raíz de un mount point.
- **Solución**: Usar Docker desde Termux (no desde Debian chroot) con los
  paquetes del root-repo, O hacer bind mount del rootfs sobre sí mismo antes del chroot.

### Error: `mount mqueue:/dev/mqueue: device or resource busy`
- **Causa**: Android ya tiene mqueue montado en /dev/mqueue y Docker intenta
  volver a montarlo dentro del contenedor.
- **Solución**: `umount /dev/mqueue` antes de arrancar dockerd.

### Error: `open /sys/fs/cgroup/cpuset/docker/cpuset.cpus: no such file or directory`
- **Causa**: Android monta cpuset con `noprefix`, por lo que los archivos se
  llaman `cpus`/`mems` en vez de `cpuset.cpus`/`cpuset.mems`.
- **Solución**: Los paquetes Termux root-repo incluyen el patch `cg-cpuset-noprefix-compat`
  en runc. Usando `dockerd` de Termux este error no ocurre.

### Error: `Devices cgroup isn't mounted`
- **Causa**: El cgroup `devices` no está montado en el entorno.
- **Solución**: El wrapper de dockerd de Termux lo monta automáticamente.
  Si se usa dockerd manual: montar cgroups antes de arrancar.

### Bootloop tras flashear kernel
- **Causa más común**: Flashear `Image.gz-dtb` (gzip) en vez de la versión descomprimida.
- **Solución**: `gunzip -c Image.gz-dtb > Image-raw` y usar `Image-raw`.
- **Recuperar**: TWRP → `dd if=/sdcard/Download/boot_backup_lineage20.img of=/dev/block/platform/11120000.ufs/by-name/BOOT`

---

## PARTE 6 — Aplicable al Samsung S4 (i9506/i9505)

El proceso de compilación es similar:
- **Cross-compile**: `arm-linux-gnueabihf-` (ARMv7, no ARM64)
- **Formato kernel**: verificar si el bootloader espera `zImage` (ARM) — probable
- **Partición BOOT**: `ls /dev/block/platform/*/by-name/` para encontrar la ruta exacta
- **Defconfig**: buscar `i9506_defconfig` o equivalente en el repo del kernel

El resto del proceso (Termux, root-repo, startdocker script) es idéntico.

---

## Resumen de backups

| Ubicación | Archivo |
|-----------|---------|
| **Local** | `/home/vito/kernel-note8/backups/` |
| **Móvil** | `/sdcard/Backups/kernel/` |
| **Nextcloud** | `note8/note8-greatlte-lineage20-boot-kernel-docker-4.4.302-g76ccdeff-2026-08-02.img` |
| **GitHub Release** | https://github.com/javivito/note8-kernel-docker/releases/tag/v1.0-docker |

---

## Referencias
- Repo compilación: https://github.com/javivito/note8-kernel-docker
- Docker en Termux: https://gist.github.com/FreddieOliveira/efe850df7ff3951cb62d74bd770dce27
- Kernel source: https://github.com/8890q/android_kernel_samsung_universal8895
- Issue cpuset noprefix: https://github.com/docker/for-linux/issues/689
