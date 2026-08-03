#!/data/data/com.termux/files/usr/bin/sh
# Termux:Boot — arranque automático de Docker en Note 8
# Instalar en: ~/.termux/boot/start_docker.sh
# Requiere: Termux:Boot instalado desde F-Droid y abierto al menos una vez

# Esperar a que el sistema arranque del todo
sleep 30

su -c 'sh /data/data/com.termux/files/home/scripts/start_docker_note8.sh'
