#!/system/bin/sh
# Magisk service.d — restaura el wrapper de docker en /debug_ramdisk en cada boot
# /debug_ramdisk está en el PATH de root pero es tmpfs (se borra al reiniciar)
# Instalar en: /data/adb/service.d/termux_path.sh
cp /sdcard/Download/docker_xbin /debug_ramdisk/docker
chmod +x /debug_ramdisk/docker
