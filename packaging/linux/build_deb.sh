#!/usr/bin/env bash
# Uso: build_deb.sh <carpeta con la app> <version> <salida.deb>   (requiere dpkg-deb; instalar el .deb sí pide root)
set -euo pipefail
APP="$1"; VER="$2"; OUT="$3"
ROOT="$(mktemp -d)"; chmod 755 "$ROOT"
mkdir -p "$ROOT/opt/oweestudent" "$ROOT/usr/bin" "$ROOT/usr/share/applications" "$ROOT/DEBIAN"
cp -r "$APP/." "$ROOT/opt/oweestudent/"
install -m 755 "$(dirname "$0")/launcher.sh" "$ROOT/usr/bin/oweestudent"
mkdir -p "$ROOT/usr/share/icons/hicolor/256x256/apps" "$ROOT/usr/share/icons/hicolor/512x512/apps"
cp "$(dirname "$0")/../../assets/icon_256.png" "$ROOT/usr/share/icons/hicolor/256x256/apps/oweestudent.png"
cp "$(dirname "$0")/../../assets/icon_512.png" "$ROOT/usr/share/icons/hicolor/512x512/apps/oweestudent.png"
cat > "$ROOT/usr/share/applications/oweestudent.desktop" <<'D'
[Desktop Entry]
Type=Application
Name=OweeStudent
Comment=Plan de estudios, repaso espaciado e IA local
Exec=/usr/bin/oweestudent
Icon=oweestudent
Terminal=false
Categories=Education;
StartupWMClass=OweeStudent
D
cat > "$ROOT/DEBIAN/control" <<C
Package: oweestudent
Version: $VER
Section: education
Priority: optional
Architecture: amd64
Depends: libmpv2 | libmpv1 | libmpv-dev, libgtk-3-0, libgstreamer1.0-0, libgstreamer-plugins-base1.0-0
Recommends: zenity, libjpeg62-turbo | libjpeg-turbo8, libgomp1, libssl3 | libssl3t64
Maintainer: Hector Martinez <hector@oweeme.com>
Homepage: https://www.oweeme.com
Description: Plan de estudios, repaso espaciado (FSRS) e IA local
 Importa planes en MD/TXT/PDF/DOCX/XLSX, genera tarjetas de repaso y sincroniza entre equipos.
C
dpkg-deb --build --root-owner-group "$ROOT" "$OUT"
