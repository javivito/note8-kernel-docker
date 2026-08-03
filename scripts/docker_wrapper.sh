#!/data/data/com.termux/files/usr/bin/sh
# Wrapper para docker — inyecta DOCKER_HOST automáticamente
#
# Instalación (como root en Termux):
#   TBIN=/data/data/com.termux/files/usr/bin
#   mv $TBIN/docker $TBIN/docker.real
#   cp docker_wrapper.sh $TBIN/docker
#   chmod +x $TBIN/docker
#
# A partir de ese momento "docker ..." funciona sin variables extra.

DOCKER_HOST=unix:///data/data/com.termux/files/usr/var/run/docker.sock \
  exec /data/data/com.termux/files/usr/bin/docker.real "$@"
