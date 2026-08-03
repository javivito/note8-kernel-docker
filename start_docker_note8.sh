#!/system/bin/sh
# Start Docker on Samsung Note 8 (greatlte, kernel 4.4.302 custom)
# Run as root: su -c sh /sdcard/Download/start_docker_note8.sh
#
# Requirements:
# - Custom kernel with BPF stubs (cmd=12->ENOENT, cmd=5 type=15->fd, cmd=8/9 attach=7->0)
# - Termux with docker package installed
# - /etc/docker/daemon.json with iptables:false, bridge:none
#
# After starting, use:
#   export DOCKER_HOST=unix:///data/data/com.termux/files/usr/var/run/docker.sock
#   docker run --rm --net=none alpine echo OK

PREFIX=/data/data/com.termux/files/usr
export PATH=$PREFIX/bin:/system/xbin:/system/bin
export DOCKER_HOST=unix://$PREFIX/var/run/docker.sock

# Kill any existing dockerd/containerd
killall dockerd containerd 2>/dev/null
sleep 2

# Start dockerd in a private mount namespace with cgroupv1
# (replaces cgroupv2 /sys/fs/cgroup with cgroupv1 controllers)
unshare -m sh -c "
  export PATH=$PREFIX/bin:/system/xbin:/system/bin

  # Replace cgroupv2 with cgroupv1 tmpfs
  mount -t tmpfs tmpfs /sys/fs/cgroup

  # Mount individual cgroupv1 controllers
  for s in devices memory cpu cpuacct freezer pids; do
    mkdir -p /sys/fs/cgroup/\$s
    mount -t cgroup -o \$s cgroup /sys/fs/cgroup/\$s 2>/dev/null
  done

  exec $PREFIX/bin/dockerd >> /sdcard/Download/dockerd.log 2>&1
" &

echo "Docker starting... wait 20 seconds"
sleep 20

if docker info > /dev/null 2>&1; then
  echo "Docker is up!"
  docker info | grep -E "Cgroup|Storage|Version"
else
  echo "Docker failed to start. Check /sdcard/Download/dockerd.log"
fi
