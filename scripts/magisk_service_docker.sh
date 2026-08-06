#!/system/bin/sh
# =============================================================================
# Magisk service.d — arranque automático de Docker en Note 8
# =============================================================================
# Instalación:
#   1. Copiar este fichero a /data/adb/service.d/termux_path.sh en el dispositivo
#   2. Copiar docker_wrapper.sh (renombrado a docker_xbin) a /data/data/com.termux/files/home/scripts/docker_xbin
#   3. Copiar start_docker_note8.sh a /data/adb/scripts/start_docker_note8.sh
#   4. Dar permisos: chmod +x /data/adb/service.d/termux_path.sh /data/adb/scripts/*
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
cp /data/data/com.termux/files/home/scripts/docker_xbin /debug_ramdisk/docker
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

# 4. Arrancar dockerd con cgroupv1, con retry si containerd tarda en arrancar
start_docker() {
  killall dockerd containerd 2>/dev/null
  sleep 3
  unshare -m sh -c "
    export PATH=$PREFIX/bin:/system/xbin:/system/bin
    mount -t tmpfs tmpfs /sys/fs/cgroup
    for s in devices memory cpu cpuacct freezer pids; do
      mkdir -p /sys/fs/cgroup/\$s
      mount -t cgroup -o \$s cgroup /sys/fs/cgroup/\$s 2>/dev/null
    done
    exec $PREFIX/bin/dockerd >> /data/data/com.termux/files/home/scripts/dockerd.log 2>&1
  " &
}

start_docker
echo "[$(date)] step5: dockerd launched (intento 1)" >> $LOG

# Esperar y comprobar si arrancó; si no, reintentar una vez
sleep 30
if ! $PREFIX/bin/docker -H unix://$PREFIX/var/run/docker.sock info > /dev/null 2>&1; then
  echo "[$(date)] step5b: docker no responde, reintentando" >> $LOG
  start_docker
  sleep 20
fi

echo "[$(date)] step6: done" >> $LOG

# 5. CPU governor a performance (Note 8 enchufado = servidor permanente)
#    A53: cpu0-3 (max 1690MHz), A73: cpu4-7 (max 2314MHz)
for cpu in 0 1 2 3 4 5 6 7; do
  echo performance > /sys/devices/system/cpu/cpu${cpu}/cpufreq/scaling_governor 2>/dev/null
done
echo "[$(date)] step7: cpu governor performance" >> $LOG
