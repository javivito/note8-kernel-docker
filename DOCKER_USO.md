# Docker en Samsung Note 8 — Guía de uso

> **Setup ya instalado en este dispositivo.** Esta guía documenta cómo está configurado
> y cómo usarlo. Si partes de cero, consulta primero `KERNEL_DOCKER_GUIDE.md`.

## Qué hay instalado

| Fichero | Ubicación | Para qué |
|---|---|---|
| Script arranque Docker | `/sdcard/Download/start_docker_note8.sh` | Arranca dockerd con cgroupv1 |
| Arranque automático | `~/.termux/boot/start_docker.sh` | Lo lanza solo al encender el móvil |
| Wrapper Termux | `/data/data/com.termux/files/usr/bin/docker` | Inyecta el socket, evita escribir DOCKER_HOST |
| Script Magisk service.d | `/data/adb/service.d/termux_path.sh` | Pone `docker` en `/debug_ramdisk` para root en cada boot |

---

## 1. Arrancar Docker

### Automático (si Termux:Boot está instalado)

No hace falta hacer nada. Al encender el móvil, Termux:Boot ejecuta
`~/.termux/boot/start_docker.sh` que espera 30 segundos y lanza Docker solo.

### Manual (desde Termux)

```sh
su -c 'sh /sdcard/Download/start_docker_note8.sh'
```

Espera ~20 segundos hasta ver "Docker is up!".

---

## 2. Usar Docker

Abrir Termux, escribir `su` y ya:

```sh
su
docker ps
docker images
docker run --rm --net=host alpine echo OK
```

No hace falta escribir nada más — el módulo Magisk y el wrapper inyectan
el PATH y el socket automáticamente.

---

## 3. Lanzar un contenedor

### Ejemplo básico

```sh
su
docker run --rm --net=host alpine echo OK
```

### Portainer (panel web de Docker)

```sh
su
docker run -d \
  --name portainer \
  --net=host \
  --restart=unless-stopped \
  -v /data/data/com.termux/files/usr/var/run/docker.sock:/var/run/docker.sock \
  -v portainer_data:/data \
  portainer/portainer-ce:latest
```

Acceder en `http://<ip-del-movil>:9000`

> **Nota sobre el socket:** Las apps que _gestionan_ Docker (Portainer, Watchtower, Traefik)
> necesitan montar el socket con `-v`. La ruta en este dispositivo es siempre:
> `/data/data/com.termux/files/usr/var/run/docker.sock`
> Las apps normales (Nextcloud, Jellyfin, etc.) no necesitan el socket.

### Redes disponibles

- `--net=host` — comparte la red del móvil ✅
- `--net=none` — sin red ✅
- `--net=bridge` — NO funciona (iptables y bridge desactivados en daemon.json)

---

## 4. Si Docker no responde

```sh
# Ver si el daemon corre
su -c 'ps aux | grep dockerd'

# Reiniciar
su -c 'killall dockerd containerd 2>/dev/null; sh /sdcard/Download/start_docker_note8.sh'
```

Log del daemon: `/sdcard/Download/dockerd.log`

---

## 5. Instalar el setup en otro dispositivo (paso a paso)

> Requisito previo: kernel custom con Docker habilitado ya flasheado. Ver `KERNEL_DOCKER_GUIDE.md`.
> El móvil debe tener **Magisk** instalado (root) y **Termux** instalado desde F-Droid.

---

### Paso 1 — Instalar docker en Termux

Abre Termux en el móvil y escribe:

```sh
pkg update
pkg install docker
```

Cuando termine, cierra Termux.

---

### Paso 2 — Crear el daemon.json

Esto le dice a Docker que no use iptables ni bridge (no funcionan en Android).

En Termux:

```sh
su
mkdir -p /etc/docker
cat > /etc/docker/daemon.json << 'EOF'
{"iptables": false, "ip-masq": false, "bridge": "none"}
EOF
exit
```

---

### Paso 3 — Copiar los scripts al móvil

Descarga desde el repositorio estos tres ficheros y ponlos en `/sdcard/Download/`:

- `start_docker_note8.sh` — arranca Docker
- `docker_xbin` — wrapper para root (es el fichero `docker_wrapper.sh` renombrado)
- `magisk_service_docker.sh` — script de arranque de Magisk

Puedes hacerlo conectando el móvil al PC por USB y copiando directamente a la carpeta
Descargas, o usando ADB:

```sh
adb push start_docker_note8.sh /sdcard/Download/start_docker_note8.sh
adb push docker_wrapper.sh /sdcard/Download/docker_xbin
adb push magisk_service_docker.sh /sdcard/Download/magisk_service_docker.sh
```

---

### Paso 4 — Instalar el wrapper en Termux

Esto hace que puedas escribir `docker` en Termux sin poner variables de entorno.

**Abre Termux** en el móvil (importante: no como root, abrir Termux normal) y escribe:

```sh
mv /data/data/com.termux/files/usr/bin/docker \
   /data/data/com.termux/files/usr/bin/docker.real

cp /sdcard/Download/docker_xbin \
   /data/data/com.termux/files/usr/bin/docker

chmod +x /data/data/com.termux/files/usr/bin/docker
```

> **Por qué desde Termux y no desde root:** Los ficheros dentro de la carpeta de Termux
> necesitan pertenecer al usuario de Termux. Si los creas como root (con `su`) Android
> les pone un identificador de seguridad incorrecto y Termux no puede usarlos,
> aunque el permiso sea correcto.

---

### Paso 5 — Instalar el script de Magisk

Esto hace que `docker` funcione también cuando escribes `su` en Termux (shell de root).
Magisk ejecuta este script en cada arranque del móvil.

En Termux:

```sh
su
cp /sdcard/Download/magisk_service_docker.sh /data/adb/service.d/termux_path.sh
chmod +x /data/adb/service.d/termux_path.sh
exit
```

---

### Paso 6 — Instalar el arranque automático (opcional pero recomendado)

Con esto Docker arranca solo al encender el móvil sin que tengas que hacer nada.

Primero instala **Termux:Boot** desde F-Droid y ábrelo una vez para que quede registrado.
Luego en Termux:

```sh
mkdir -p ~/.termux/boot

cat > ~/.termux/boot/start_docker.sh << 'EOF'
#!/data/data/com.termux/files/usr/bin/sh
sleep 30
su -c 'sh /sdcard/Download/start_docker_note8.sh'
EOF

chmod +x ~/.termux/boot/start_docker.sh
```

> El `sleep 30` es necesario para que el sistema termine de arrancar antes de lanzar Docker.
> Sin él, Docker falla porque el kernel aún no está listo.

> **Igual que en el paso 4:** hacerlo desde Termux, nunca como root externo.

---

### Paso 7 — Reiniciar y verificar

Reinicia el móvil. Después de ~50 segundos, abre Termux y prueba:

```sh
su
docker ps
```

Si ves una tabla (aunque esté vacía) es que todo funciona.

Si falla, arranca Docker manualmente:

```sh
su -c 'sh /sdcard/Download/start_docker_note8.sh'
```

Y vuelve a probar `docker ps`.

---

## Fallos conocidos y soluciones

### `bpf_prog_query failed: invalid argument`
Samsung LSM bloquea BPF. El kernel custom tiene stubs que lo evitan, y el script
de arranque usa cgroupv1 con `unshare -m` para que Docker no necesite BPF.

### Kernel panic con `--net=host`
Fix en `ipc/namespace.c`: `ns->user_ns = get_user_ns()` debe ir ANTES de `mq_init_ns(ns)`.

### Contenedor arranca con rootfs vacío
- Pull interrumpido: `docker rmi <imagen> && docker pull --platform linux/arm64 <imagen>`
- Archivo `link` vacío en overlay2: `printf 'SHORTID' > overlay2/<id>/link`

### `exec format error`
Imagen descargada era amd64. Usar siempre `--platform linux/arm64`.

### WiFi se duerme con ADB
`adb shell svc wifi enable`
