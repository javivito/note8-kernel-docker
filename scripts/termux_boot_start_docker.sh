#!/data/data/com.termux/files/usr/bin/sh
# Termux:Boot — arranque automático de Docker en Note 8
# Instalar en: ~/.termux/boot/start_docker.sh
# Requiere: Termux:Boot instalado desde F-Droid y abierto al menos una vez

# Esperar a que el sistema arranque del todo
sleep 30

su -c 'sh /data/data/com.termux/files/home/scripts/start_docker_note8.sh'

# Tailscale
PREFIX=/data/data/com.termux/files/usr
mkdir -p $PREFIX/var/run $PREFIX/var/lib/tailscale $PREFIX/var/log
$PREFIX/bin/tailscaled \
  --tun=userspace-networking \
  --statedir=$PREFIX/var/lib/tailscale \
  --socket=$PREFIX/var/run/tailscale.sock \
  >> $PREFIX/var/log/tailscaled.log 2>&1 &
