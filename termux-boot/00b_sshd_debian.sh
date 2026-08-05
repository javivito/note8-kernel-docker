#!/data/data/com.termux/files/usr/bin/sh
# Termux:Boot — SSH Debian chroot (puerto 22)
# Instalar en: ~/.termux/boot/00b_sshd_debian.sh

nohup chroot-distro login debian --shared-tmp -- sh -c '
# Fix devpts para que funcionen PTYs (SSH interactivo con prompt)
umount /dev/pts 2>/dev/null
mount -t devpts -o newinstance,ptmxmode=0666,mode=0620,gid=5 devpts /dev/pts
ln -sf /dev/pts/ptmx /dev/ptmx
# Montar /proc (necesario para htop, ps, etc.)
mount -t proc proc /proc 2>/dev/null || true
exec /usr/sbin/sshd -D
' >> /data/data/com.termux/files/usr/var/log/sshd_debian.log 2>&1 &
