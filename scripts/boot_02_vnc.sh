#!/data/data/com.termux/files/usr/bin/sh
# Termux:Boot — XFCE (via startdebian) + x11vnc en chroot + noVNC
# Instalar en: ~/.termux/boot/02_vnc.sh

PREFIX=/data/data/com.termux/files/usr
HOME=/data/data/com.termux/files/home

# Esperar a que el sistema esté listo
sleep 45

# 1. Arrancar Debian con termux-x11 + XFCE (igual que startdebian manual)
nohup $HOME/bin/startdebian >> $PREFIX/var/log/xfce.log 2>&1 &

# Esperar a que XFCE arranque dentro del chroot
sleep 20

# 2. x11vnc dentro del chroot — comparte el display :1 de termux-x11 via VNC (puerto 5901)
nohup chroot-distro login debian --shared-tmp -- bash -c '
  x11vnc -display :1 -forever -nopw -quiet -rfbport 5901
' >> $PREFIX/var/log/x11vnc.log 2>&1 &

# 3. noVNC en Termux — acceso web en puerto 6080 → VNC 5901
sleep 3
nohup websockify --web=$HOME/novnc 6080 localhost:5901 \
  >> $PREFIX/var/log/novnc.log 2>&1 &
