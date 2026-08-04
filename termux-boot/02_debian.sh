#!/data/data/com.termux/files/usr/bin/sh
# Termux:Boot — Debian chroot + XFCE via termux-x11
# Instalar en: ~/.termux/boot/02_debian.sh

PREFIX=/data/data/com.termux/files/usr
HOME=/data/data/com.termux/files/home

sleep 45

# Inicializar actividad de termux-x11 en Android para que las apps rendericen correctamente
am start --user 0 -n com.termux.x11/com.termux.x11.MainActivity > /dev/null 2>&1
sleep 2

nohup $HOME/bin/startdebian >> $PREFIX/var/log/xfce.log 2>&1 &
