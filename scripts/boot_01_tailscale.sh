#!/data/data/com.termux/files/usr/bin/sh
# Termux:Boot — Tailscale
# Instalar en: ~/.termux/boot/01_tailscale.sh

PREFIX=/data/data/com.termux/files/usr

sleep 15

mkdir -p $PREFIX/var/run $PREFIX/var/lib/tailscale $PREFIX/var/log
nohup $PREFIX/bin/tailscaled \
  --tun=userspace-networking \
  --statedir=$PREFIX/var/lib/tailscale \
  --socket=$PREFIX/var/run/tailscale.sock \
  >> $PREFIX/var/log/tailscaled.log 2>&1 &
