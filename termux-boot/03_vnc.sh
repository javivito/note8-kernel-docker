#!/data/data/com.termux/files/usr/bin/sh
# Termux:Boot — x11vnc (comparte display :1 via VNC puerto 5901)
# Instalar en: ~/.termux/boot/03_vnc.sh
# Requiere: 02_debian.sh corriendo (termux-x11 en :1 con XFCE)

PREFIX=/data/data/com.termux/files/usr

# Esperar a que XFCE esté levantado
sleep 70

# Loop de reinicio: si x11vnc cae (XIO error, señal, etc.) se relanza automáticamente
while true; do
    DISPLAY=:1 x11vnc -display :1 -forever -nopw -quiet -rfbport 5901 \
      >> $PREFIX/var/log/x11vnc.log 2>&1
    echo "$(date): x11vnc terminó, reiniciando en 5s..." >> $PREFIX/var/log/x11vnc.log
    sleep 5
    # Esperar a que el display :1 esté disponible antes de reintentar
    while ! DISPLAY=:1 xdpyinfo > /dev/null 2>&1; do
        sleep 3
    done
done &
