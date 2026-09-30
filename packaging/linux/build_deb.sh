#!/usr/bin/env bash
# Uso: build_deb.sh <carpeta con la app> <version> <salida.deb>   (requiere dpkg-deb; instalar el .deb sí pide root)
set -euo pipefail
APP="$1"; VER="$2"; OUT="$3"
ROOT="$(mktemp -d)"; chmod 755 "$ROOT"
mkdir -p "$ROOT/opt/oweestudent" "$ROOT/usr/bin" "$ROOT/usr/share/applications" "$ROOT/DEBIAN"
cp -r "$APP/." "$ROOT/opt/oweestudent/"
cat > "$ROOT/usr/bin/oweestudent" <<'W'
#!/bin/sh
# libmpv.so.1 puede faltar en distros nuevas: se usa libmpv.so.2 mediante un enlace en el directorio del usuario
L="${XDG_DATA_HOME:-$HOME/.local/share}/oweestudent/lib"
if ! ldconfig -p 2>/dev/null | grep -q "libmpv.so.1"; then
  M="$(ldconfig -p 2>/dev/null | awk '/libmpv.so.2/{print $NF; exit}')"
  [ -n "$M" ] && mkdir -p "$L" && ln -sf "$M" "$L/libmpv.so.1" && export LD_LIBRARY_PATH="$L${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi
exec /opt/oweestudent/OweeStudent "$@"
W
chmod 755 "$ROOT/usr/bin/oweestudent"
cat > "$ROOT/usr/share/applications/oweestudent.desktop" <<'D'
[Desktop Entry]
Type=Application
Name=OweeStudent
Comment=Plan de estudios, repaso espaciado e IA local
Exec=/usr/bin/oweestudent
Terminal=false
Categories=Education;
D
cat > "$ROOT/DEBIAN/control" <<C
Package: oweestudent
Version: $VER
Section: education
Priority: optional
Architecture: amd64
Depends: libmpv2 | libmpv1, libgtk-3-0
Recommends: zenity
Maintainer: Hector Martinez <hector@oweeme.com>
Homepage: https://www.oweeme.com
Description: Plan de estudios, repaso espaciado (FSRS) e IA local
 Importa planes en MD/TXT/PDF/DOCX/XLSX, genera tarjetas de repaso y sincroniza entre equipos.
C
dpkg-deb --build --root-owner-group "$ROOT" "$OUT"
