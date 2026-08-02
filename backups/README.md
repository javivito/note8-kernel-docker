# Note 8 Kernel Backup — Docker Support

## Archivo: `note8-greatlte-boot-kernel-docker-4.4.302-g76ccdeff-2026-08-02.img`

### Descripción
Boot partition completa (40MB) del Samsung Galaxy Note 8 SM-N950F (greatltexx)
con kernel custom compilado para soporte Docker.

### Dispositivo
- Modelo: Samsung Galaxy Note 8 SM-N950F (greatltexx, Exynos 8895)
- ROM: LineageOS 20 (Android 13) by ivanmeler
- Magisk: 27.0 (root activo, Knox quemado)

### Kernel
- Versión: `4.4.302-g76ccdeff`
- Fuente: https://github.com/8890q/android_kernel_samsung_universal8895 rama `lineage-19.1`
- Defconfig: `exynos8895-greatlte_defconfig`
- Compilado: GitHub Actions ubuntu-22.04, gcc-9-aarch64-linux-gnu
- Repo de compilación: https://github.com/javivito/note8-kernel-docker

### Opciones Docker añadidas
- `CONFIG_BRIDGE=y` — Bridge de red para contenedores
- `CONFIG_BRIDGE_NETFILTER=y` — Netfilter sobre bridge
- `CONFIG_OVERLAY_FS=y` — OverlayFS (storage driver de Docker)
- `CONFIG_VETH=y` — Virtual ethernet (ya presente en stock)
- `CONFIG_NET_NS=y` — Network namespaces (ya presente en stock)

### Cómo restaurar
```bash
# Desde TWRP o recovery con ADB:
dd if=note8-greatlte-boot-kernel-docker-4.4.302-g76ccdeff-2026-08-02.img \
   of=/dev/block/platform/11120000.ufs/by-name/BOOT bs=4096

# O con fastboot:
fastboot flash boot note8-greatlte-boot-kernel-docker-4.4.302-g76ccdeff-2026-08-02.img
```

### Nota técnica importante
El bootloader de greatlte espera el kernel en formato **ARM64 Image raw (sin comprimir)**.
Al recompilar, el build genera `Image.gz-dtb` (gzip) — hay que descomprimir con
`gunzip -c Image.gz-dtb > Image-raw` antes de empacar con magiskboot.

### Fecha
2026-08-02
