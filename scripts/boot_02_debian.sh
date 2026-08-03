#!/data/data/com.termux/files/usr/bin/sh
# Termux:Boot — Debian chroot + XFCE via termux-x11
# Instalar en: ~/.termux/boot/02_debian.sh

PREFIX=/data/data/com.termux/files/usr
HOME=/data/data/com.termux/files/home

sleep 45

nohup $HOME/bin/startdebian >> $PREFIX/var/log/xfce.log 2>&1 &
