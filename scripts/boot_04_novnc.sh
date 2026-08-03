#!/data/data/com.termux/files/usr/bin/sh
# Termux:Boot — noVNC (acceso web al VNC en puerto 6080)
# Instalar en: ~/.termux/boot/04_novnc.sh
# Requiere: 03_vnc.sh corriendo (x11vnc en puerto 5901)

PREFIX=/data/data/com.termux/files/usr
HOME=/data/data/com.termux/files/home

sleep 75

nohup websockify --web=$HOME/novnc 6080 localhost:5901 \
  >> $PREFIX/var/log/novnc.log 2>&1 &
