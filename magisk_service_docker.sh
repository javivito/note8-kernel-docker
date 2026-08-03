#!/system/bin/sh
# Magisk service.d — ejecutado como root en cada boot por Magisk
# Instalar en: /data/adb/service.d/termux_path.sh
#
# Ficheros necesarios en /data/adb/:
#   docker_xbin          — wrapper docker para root
#   start_docker_note8.sh — script que arranca dockerd

# 1. Wrapper docker en PATH de root (/debug_ramdisk es tmpfs en PATH de root)
cp /data/adb/docker_xbin /debug_ramdisk/docker
chmod +x /debug_ramdisk/docker

# 2. ADB WiFi permanente (puerto 5555)
setprop service.adb.tcp.port 5555
stop adbd
start adbd

# 3. Arrancar Docker en background tras esperar a que el sistema esté listo
(
  sleep 45
  export PATH=/data/data/com.termux/files/usr/bin:/system/xbin:/system/bin
  sh /data/adb/start_docker_note8.sh >> /sdcard/Download/dockerd_boot.log 2>&1
) &
