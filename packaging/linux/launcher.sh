#!/bin/sh
# Lanzador de OweeStudent. Resuelve libmpv.so.1 (que Flet exige pero las distros nuevas traen como .so.2),
# guarda un log y muestra un aviso legible si la app no puede abrir.
APP_DIR="${OWEE_APP_DIR:-/opt/oweestudent}"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}/oweestudent"
LOG="$DATA/ultimo-error.log"
mkdir -p "$DATA/lib" 2>/dev/null

aviso() {  # aviso "texto"
  if command -v zenity >/dev/null 2>&1; then zenity --error --title="OweeStudent" --no-markup --text="$1" 2>/dev/null
  elif command -v kdialog >/dev/null 2>&1; then kdialog --error "$1" 2>/dev/null
  elif command -v notify-send >/dev/null 2>&1; then notify-send "OweeStudent" "$1"
  elif command -v xmessage >/dev/null 2>&1; then xmessage "$1"
  fi
  echo "$1" >&2
}

# Busca libmpv sin depender de ldconfig (en Debian no está en el PATH de un usuario normal)
MPV=""
for d in /usr/lib/x86_64-linux-gnu /usr/lib64 /usr/lib /lib/x86_64-linux-gnu /usr/local/lib; do
  for f in "$d"/libmpv.so.1 "$d"/libmpv.so.2 "$d"/libmpv.so.2.*; do
    if [ -e "$f" ]; then MPV="$f"; break 2; fi
  done
done
case "$MPV" in
  "") aviso "Falta la librería libmpv. Instálala una vez con:
sudo apt install libmpv2
y vuelve a abrir OweeStudent."; exit 1 ;;
  */libmpv.so.1) ;;   # ya existe con el nombre que se necesita
  *) ln -sf "$MPV" "$DATA/lib/libmpv.so.1"
     export LD_LIBRARY_PATH="$DATA/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" ;;
esac

: > "$LOG"
"$APP_DIR/OweeStudent" "$@" 2>>"$LOG"
RC=$?
if [ "$RC" -ne 0 ] || grep -q "error while loading shared libraries" "$LOG" 2>/dev/null; then
  FALTA="$(grep -o 'lib[^:]*\.so[^:]*: cannot open' "$LOG" | head -1 | cut -d: -f1)"
  aviso "OweeStudent no pudo abrir${FALTA:+ (falta $FALTA)}.
Detalles en: $LOG"
fi
exit "$RC"
