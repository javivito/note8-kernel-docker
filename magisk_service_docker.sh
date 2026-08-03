#!/system/bin/sh
# =============================================================================
# Magisk service.d — arranque automático de Docker en Note 8
# =============================================================================
# Instalación:
#   1. Copiar este fichero a /data/adb/service.d/termux_path.sh en el dispositivo
#   2. Copiar docker_wrapper.sh (renombrado a docker_xbin) a /data/adb/docker_xbin
#   3. Dar permisos de ejecución: chmod +x /data/adb/service.d/termux_path.sh
#
# IMPORTANTE: Escribir estos ficheros desde nsenter en el namespace de magiskd,
# NO desde adb shell su -c (contexto SELinux incorrecto):
#   adb shell su -c 'nsenter --mount=/proc/<PID_magiskd>/ns/mnt -- /system/bin/sh'
#   (PID de magiskd: adb shell su -c 'ps -A | grep magiskd')
#
# Este script es ejecutado por Magisk como root en cada arranque del dispositivo.
# Magisk lo lanza en background, por lo que sleep/esperas no bloquean el boot.
# =============================================================================

LOG=/data/adb/boot.log
PREFIX=/data/data/com.termux/files/usr
export PATH=$PREFIX/bin:/system/xbin:/system/bin

echo "[$(date)] step1: start" > $LOG

# 1. Wrapper docker en /debug_ramdisk (tmpfs que está en el PATH de root)
#    Esto permite usar 'docker' desde cualquier shell root sin escribir PATH
cp /data/adb/docker_xbin /debug_ramdisk/docker
chmod +x /debug_ramdisk/docker

echo "[$(date)] step2: docker wrapper ok" >> $LOG

# 2. ADB sobre WiFi permanente (puerto 5555)
#    Permite conectar con 'adb connect <ip>:5555' sin cable tras cada reboot
setprop service.adb.tcp.port 5555
stop adbd
start adbd

echo "[$(date)] step3: adb wifi ok" >> $LOG

# 3. Esperar a que el sistema esté completamente listo
sleep 45
echo "[$(date)] step4: sleep done, starting docker" >> $LOG

# 4. Arrancar dockerd con cgroupv1 (requerido en kernel 4.4 con Samsung LSM)
#    unshare -m crea un namespace de mount privado donde montamos cgroupv1
#    sustituyendo el cgroupv2 del sistema (que requeriría BPF, bloqueado por Samsung)
killall dockerd containerd 2>/dev/null
sleep 2

unshare -m sh -c "
  export PATH=$PREFIX/bin:/system/xbin:/system/bin
  mount -t tmpfs tmpfs /sys/fs/cgroup
  for s in devices memory cpu cpuacct freezer pids; do
    mkdir -p /sys/fs/cgroup/\$s
    mount -t cgroup -o \$s cgroup /sys/fs/cgroup/\$s 2>/dev/null
  done
  exec $PREFIX/bin/dockerd >> /sdcard/Download/dockerd.log 2>&1
" &

echo "[$(date)] step5: dockerd launched" >> $LOG
sleep 25
echo "[$(date)] step6: done" >> $LOG
