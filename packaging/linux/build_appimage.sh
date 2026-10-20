#!/usr/bin/env bash
# Uso: build_appimage.sh <carpeta con la app> <version> <salida.AppImage>
# Un único archivo que se ejecuta sin instalar (chmod +x y doble clic). Necesita libmpv del sistema, como el .deb.
set -euo pipefail
APP="$1"; VER="$2"; OUT="$3"
AQUI="$(cd "$(dirname "$0")" && pwd)"
AD="$(mktemp -d)/OweeStudent.AppDir"
mkdir -p "$AD/usr/lib/oweestudent" "$AD/usr/bin"
cp -r "$APP/." "$AD/usr/lib/oweestudent/"
install -m 755 "$AQUI/launcher.sh" "$AD/usr/bin/oweestudent"
cp "$AQUI/../../assets/icon_256.png" "$AD/oweestudent.png"
cat > "$AD/oweestudent.desktop" <<D
[Desktop Entry]
Type=Application
Name=OweeStudent
Comment=Plan de estudios, repaso espaciado e IA local
Exec=oweestudent
Icon=oweestudent
Terminal=false
Categories=Education;
X-AppImage-Version=$VER
D
cat > "$AD/AppRun" <<'R'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
export OWEE_APP_DIR="$HERE/usr/lib/oweestudent"
exec "$HERE/usr/bin/oweestudent" "$@"
R
chmod 755 "$AD/AppRun"
HERR="${APPIMAGETOOL:-}"
if [ -z "$HERR" ]; then
  HERR="$(mktemp -d)/appimagetool"
  curl -fsSL -o "$HERR" https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
  chmod +x "$HERR"
fi
ARCH=x86_64 "$HERR" --appimage-extract-and-run "$AD" "$OUT"
