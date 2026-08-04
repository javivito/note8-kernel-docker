#!/data/data/com.termux/files/usr/bin/sh
# Termux:Boot — SSH Debian chroot (puerto 22)
# Instalar en: ~/.termux/boot/00b_sshd_debian.sh

nohup chroot-distro login debian --shared-tmp -- /usr/sbin/sshd -D >> /data/data/com.termux/files/usr/var/log/sshd_debian.log 2>&1 &
