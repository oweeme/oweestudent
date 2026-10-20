#!/usr/bin/env bash
# Uso: build_dmg.sh <OweeStudent.app> <version> <salida.dmg>   (solo en macOS; sin firmar ni notarizar)
set -euo pipefail
APP="$1"; VER="$2"; OUT="$3"
TMP="$(mktemp -d)"
cp -R "$APP" "$TMP/"
ln -s /Applications "$TMP/Applications"
hdiutil create -volname "OweeStudent $VER" -srcfolder "$TMP" -ov -format UDZO "$OUT"
