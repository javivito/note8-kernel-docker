#!/data/data/com.termux/files/usr/bin/sh
# Termux:Boot — x11vnc (comparte display :1 via VNC puerto 5901)
# Instalar en: ~/.termux/boot/03_vnc.sh
# Requiere: 02_debian.sh corriendo (termux-x11 en :1 con XFCE)

PREFIX=/data/data/com.termux/files/usr

# Esperar a que XFCE esté levantado
sleep 70

# x11vnc corre en Termux (no en el chroot) para tener acceso al Xauthority
DISPLAY=:1 nohup x11vnc -display :1 -forever -nopw -quiet -rfbport 5901 \
  >> $PREFIX/var/log/x11vnc.log 2>&1 &
