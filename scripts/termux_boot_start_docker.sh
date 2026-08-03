#!/data/data/com.termux/files/usr/bin/sh
# Termux:Boot — arranque automático de Docker, Tailscale, VNC y noVNC en Note 8
# Instalar en: ~/.termux/boot/start_docker.sh
# Requiere: Termux:Boot instalado desde F-Droid y abierto al menos una vez

PREFIX=/data/data/com.termux/files/usr
HOME=/data/data/com.termux/files/home
export PATH=$PREFIX/bin:$PATH

# Esperar a que el sistema arranque del todo
sleep 30

# Docker (como root via Magisk)
su -c 'sh /data/data/com.termux/files/home/scripts/start_docker_note8.sh'

# Tailscale
mkdir -p $PREFIX/var/run $PREFIX/var/lib/tailscale $PREFIX/var/log
$PREFIX/bin/tailscaled \
  --tun=userspace-networking \
  --statedir=$PREFIX/var/lib/tailscale \
  --socket=$PREFIX/var/run/tailscale.sock \
  >> $PREFIX/var/log/tailscaled.log 2>&1 &

sleep 3

# VNC — XFCE en display :1, puerto 5901
vncserver :1 -geometry 1280x720 -depth 24 >> $PREFIX/var/log/vnc.log 2>&1

# noVNC — acceso web en puerto 6080 → redirige a VNC 5901
# (--daemon no funciona en Android por setgid bloqueado, usamos nohup &)
nohup websockify --web=$HOME/novnc 6080 localhost:5901 >> $PREFIX/var/log/novnc.log 2>&1 &
