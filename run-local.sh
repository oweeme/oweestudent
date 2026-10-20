#!/bin/sh
# Ejecuta OweeStudent en tu equipo con DATOS DE PRUEBA (no toca tu base real en ~/.oweestudent).
#   ./run-local.sh          ventana de escritorio
#   ./run-local.sh --web    servidor en http://localhost:8550 (también sirve para probar en el móvil)
# El cliente gráfico de Flet pide libmpv.so.1; las distribuciones nuevas traen libmpv.so.2. Se enlaza en tu carpeta de usuario.
DIR="$(cd "$(dirname "$0")" && pwd)"
LIB="$HOME/.local/lib/owee"
if [ ! -e "$LIB/libmpv.so.1" ]; then
  for f in /usr/lib/x86_64-linux-gnu/libmpv.so.1 /usr/lib/x86_64-linux-gnu/libmpv.so.2 /usr/lib64/libmpv.so.2 /usr/lib/libmpv.so.2; do
    if [ -e "$f" ]; then mkdir -p "$LIB" && ln -sf "$f" "$LIB/libmpv.so.1"; break; fi
  done
fi
[ -e "$LIB/libmpv.so.1" ] || echo "Aviso: no encuentro libmpv. Instálala con:  sudo apt install libmpv2   (o usa --web)" >&2
export LD_LIBRARY_PATH="$LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export OWEE_DB="${OWEE_DB:-/tmp/owee-prueba.db}" FLET_APP_STORAGE_DATA="${FLET_APP_STORAGE_DATA:-/tmp/owee-prueba}"
exec "$DIR/.venv/bin/python" "$DIR/main.py" "$@"
