# Guía: Compilar kernel con Docker para greatlte/Note8 (y S4)

## Objetivo
Compilar un kernel custom con soporte Docker para Samsung Galaxy Note 8 (greatlte, Exynos 8895)
ejecutando LineageOS 20 (Android 13) con Magisk.

## Pasos que funcionaron

### 1. Repositorio de compilación
- GitHub público: `javivito/note8-kernel-docker`
- Workflow: `.github/workflows/build.yml`
- Ficheros necesarios: `docker.fragment` con opciones Docker

### 2. Fuente del kernel correcta
```
Repo:   https://github.com/8890q/android_kernel_samsung_universal8895
Rama:   lineage-19.1
Kernel: 4.4.302 (mismo que el dispositivo — 8890q = organización de ivanmeler)
```
**Importante**: NO usar `ivanmeler/android_kernel_samsung_universal8895 seals-pie-new`
— ese es kernel 4.4.111 (Android 9), incompatible con LineageOS 20.

### 3. Defconfig
```
exynos8895-greatlte_defconfig
```
Ubicado en `arch/arm64/configs/exynos8895-greatlte_defconfig`.

### 4. Config Docker (docker.fragment)
```
CONFIG_BRIDGE=y
CONFIG_BRIDGE_NETFILTER=y
CONFIG_OVERLAY_FS=y
```
(CONFIG_VETH y CONFIG_NET_NS ya estaban presentes en el defconfig)

### 5. Config RKP/TIMA (Knox desactivado)
```
CONFIG_RKP=n
CONFIG_RKP_KDP=n
CONFIG_RKP_NS_PROT=n
CONFIG_RKP_DMAP_PROT=n
CONFIG_RKP_6G=n
CONFIG_RKP_CFP=n
CONFIG_RKP_CFP_JOPP=n
CONFIG_TIMA=n
CONFIG_TIMA_LOG=n
```

### 6. Compilación (GitHub Actions)
```yaml
- uses: actions/checkout@v4
- apt-get install gcc-9-aarch64-linux-gnu binutils-aarch64-linux-gnu bc bison flex libssl-dev libelf-dev python3 make git libncurses-dev zip
- ln -sf /usr/bin/aarch64-linux-gnu-gcc-9 /usr/local/bin/aarch64-linux-gnu-gcc
- git clone --depth=1 --branch lineage-19.1 https://github.com/8890q/android_kernel_samsung_universal8895 kernel
- cd kernel && make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- exynos8895-greatlte_defconfig
- cat docker.fragment >> .config && [RKP desactiv.] && make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- olddefconfig
- make -j$(nproc) ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- HOSTCFLAGS="-fcommon" KCFLAGS="-Wno-error" Image.gz-dtb
```

### 7. ⚠️ CRÍTICO: Formato del kernel para greatlte

El bootloader de greatlte espera el kernel en formato **ARM64 Image RAW (sin comprimir)**.
El build genera `Image.gz-dtb` (gzip) — hay que **descomprimirlo** antes de empacar:

```bash
gunzip -c Image.gz-dtb > Image-raw
# Nota: el error "trailing garbage ignored" es normal (son los DTBs al final del gz)
```

Verificar formato correcto:
```bash
xxd Image-raw | head -1
# Debe empezar con: 10 00 00 14  (instrucción ARM64, no 1f 8b de gzip)
```

### 8. Flasheo con magiskboot

```bash
# En el dispositivo con root:
cd /data/local/tmp
/data/adb/magisk/magiskboot unpack /sdcard/Download/boot_backup_lineage20.img
# Copiar el kernel descomprimido:
cp /sdcard/Download/Image-raw kernel
# Reempacar (mantiene ramdisk y extra/DTBs del original):
/data/adb/magisk/magiskboot repack /sdcard/Download/boot_backup_lineage20.img /sdcard/Download/new-boot.img
# Flashear:
dd if=/sdcard/Download/new-boot.img of=/dev/block/platform/11120000.ufs/by-name/BOOT bs=4096
sync
```

### 9. Verificación post-flash
```bash
adb shell su -c "cat /proc/config.gz | gunzip | grep -E 'CONFIG_BRIDGE=|CONFIG_OVERLAY_FS=|CONFIG_VETH=|CONFIG_NET_NS='"
# Debe mostrar: CONFIG_BRIDGE=y, CONFIG_OVERLAY_FS=y, CONFIG_VETH=y, CONFIG_NET_NS=y
```

---

## Partición BOOT de greatlte
```
/dev/block/platform/11120000.ufs/by-name/BOOT
```

## Errores encontrados y soluciones

| Error | Causa | Solución |
|-------|-------|----------|
| Bootloop tras flash | Image.gz-dtb (gzip) en lugar de Image raw | `gunzip -c Image.gz-dtb > Image-raw` |
| Bootloop tras flash | Kernel 4.4.111 (seals-pie-new) incompatible con LOS20 | Usar 8890q/lineage-19.1 (4.4.302) |
| `yylloc` build error | GCC 10+ con DTC antiguo | `HOSTCFLAGS="-fcommon"` |
| Werror varios | GCC 12 demasiado estricto para kernel 4.4 | Usar gcc-9-aarch64-linux-gnu + `KCFLAGS="-Wno-error"` |
| `vmm.6g.elf not found` | Samsung Knox RKP blob | Desactivar todos CONFIG_RKP/TIMA |

---

## Para Samsung S4 (i9506/i9505, Exynos 4412)

El proceso es similar pero con diferencias:
- **Defconfig**: buscar `i9506_defconfig` o `crespo_defconfig` según variante
- **Cross-compile**: `arm-linux-gnueabihf-` (ARMv7, no ARM64)
- **Partición BOOT**: diferente path — verificar con `ls /dev/block/platform/*/by-name/`
- **Formato kernel**: verificar si el bootloader espera `zImage` o `Image`
- **Fuente**: buscar en `LineageOS/android_kernel_samsung_*` según modelo exacto

El proceso de magiskboot repack es idéntico.

---

## Backups del kernel Note8 Docker
- **Local**: `/home/vito/kernel-note8/backups/`
- **GitHub Release**: https://github.com/javivito/note8-kernel-docker/releases/tag/v1.0-docker
- **Nextcloud**: `note8/note8-greatlte-lineage20-boot-kernel-docker-4.4.302-g76ccdeff-2026-08-02.img`
- **Móvil**: `/sdcard/Backups/kernel/`
