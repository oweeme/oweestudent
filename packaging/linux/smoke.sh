#!/bin/bash
# Prueba de humo dentro de un Debian 12 limpio: ¿abre la app con solo las dependencias del .deb?
# Uso (en un contenedor debian:12):  bash /pk/smoke.sh     con /app = carpeta de la app y /pk = packaging/linux
set -u
apt-get update -qq >/dev/null 2>&1
DEPS="libmpv2 libgtk-3-0 libgstreamer1.0-0 libgstreamer-plugins-base1.0-0 xvfb xauth libegl1 libgl1 libgl1-mesa-dri libjpeg62-turbo"
apt-get install -y -qq --no-install-recommends $DEPS >/dev/null 2>&1 || { echo "FALLO: no se pudieron instalar dependencias"; exit 2; }
export HOME=/root OWEE_APP_DIR=/app OWEE_DB=/tmp/t.db LIBGL_ALWAYS_SOFTWARE=1
cp /pk/launcher.sh /tmp/l.sh; chmod +x /tmp/l.sh
xvfb-run -a -s "-screen 0 1280x800x24" timeout 20 /tmp/l.sh >/tmp/out.log 2>&1
LOG=/root/.local/share/oweestudent/ultimo-error.log
echo "--- errores de la app:"; grep -v "CRITICAL\|^$\|Gtk-WARNING\|dbus\|portal" "$LOG" | head -8
if grep -q "error while loading shared libraries\|symbol lookup error\|Failed to load Python" "$LOG"; then
  echo "FALLO: la app no puede cargar sus librerías"; exit 1
fi
if [ ! -f /tmp/t.db ]; then echo "FALLO: la app no llegó a arrancar (no creó su base de datos)"; exit 1; fi
echo "OK: la app arrancó en Debian 12 limpio"
