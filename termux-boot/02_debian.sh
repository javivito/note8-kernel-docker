#!/data/data/com.termux/files/usr/bin/sh
# Termux:Boot — Debian chroot + XFCE via termux-x11
# Instalar en: ~/.termux/boot/02_debian.sh

PREFIX=/data/data/com.termux/files/usr
HOME=/data/data/com.termux/files/home

sleep 45

# Arrancar termux-x11 primero y esperar a que genere ~/.Xauthority
termux-x11 :1 > /dev/null 2>&1 &
sleep 5
am start --user 0 -n com.termux.x11/com.termux.x11.MainActivity > /dev/null 2>&1
sleep 3

# startdebian verá termux-x11 ya corriendo y lanzará XFCE con el Xauthority listo
nohup $HOME/bin/startdebian >> $PREFIX/var/log/xfce.log 2>&1 &
