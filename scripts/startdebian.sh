#!/data/data/com.termux/files/usr/bin/bash
export PATH=/data/data/com.termux/files/usr/bin:$PATH
export PREFIX=/data/data/com.termux/files/usr

# Arrancar X11 si no está corriendo ya
if ! pgrep -x termux-x11 > /dev/null; then
    termux-x11 :1 &
    sleep 3
fi

# Entrar al chroot como root, enmascarar /dev/video*, luego lanzar xfce4 como vito
chroot-distro login debian --shared-tmp -- bash -c '
# Fix devpts para que funcionen PTYs (SSH interactivo)
umount /dev/pts 2>/dev/null
mount -t devpts -o newinstance,ptmxmode=0666,mode=0620,gid=5 devpts /dev/pts
ln -sf /dev/pts/ptmx /dev/ptmx 2>/dev/null
# Enmascarar cámaras
for v in /dev/video*; do
    mount --bind /dev/null "$v" 2>/dev/null
done
exec su - vito -c "export DISPLAY=:1; export DBUS_SESSION_BUS_ADDRESS=; exec dbus-launch --exit-with-session startxfce4"
'
