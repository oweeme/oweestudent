#!/usr/bin/env bash
# Instala OweeStudent SOLO para tu usuario (~/.local). No necesita sudo.
set -euo pipefail
AQUI="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/.local/opt/oweestudent"
BIN="$HOME/.local/bin"
APPS="$HOME/.local/share/applications"

mkdir -p "$DEST" "$BIN" "$APPS"
rm -rf "$DEST"/*
cp -r "$AQUI/app/." "$DEST/"
[ -f "$AQUI/oweestudent.png" ] && cp "$AQUI/oweestudent.png" "$DEST/oweestudent.png" || true

cp "$AQUI/launcher.sh" "$DEST/launcher.sh" && chmod +x "$DEST/launcher.sh"
cat > "$BIN/oweestudent" <<WRAP
#!/bin/sh
export OWEE_APP_DIR="$DEST"
exec "$DEST/launcher.sh" "\$@"
WRAP
chmod +x "$BIN/oweestudent"

cat > "$APPS/oweestudent.desktop" <<DESK
[Desktop Entry]
Type=Application
Name=OweeStudent
Comment=Plan de estudios, repaso espaciado e IA local
Exec=$BIN/oweestudent
Icon=$DEST/oweestudent.png
Terminal=false
Categories=Education;
DESK
command -v update-desktop-database >/dev/null && update-desktop-database "$APPS" 2>/dev/null || true

echo "✅ Instalado en $DEST"
echo "   Ábrelo desde el menú de aplicaciones o con:  oweestudent"
case ":$PATH:" in *":$BIN:"*) ;; *) echo "   (Añade $BIN a tu PATH para usar el comando 'oweestudent')";; esac
for l in libgomp.so.1 libssl.so.3; do ls /usr/lib/x86_64-linux-gnu/$l /usr/lib64/$l >/dev/null 2>&1 || echo "   Consejo: para la IA integrada instala libgomp1 y libssl3 (sudo apt install libgomp1 libssl3)"; done | sort -u
command -v zenity >/dev/null || echo "   Consejo: instala 'zenity' para el selector de archivos (sudo apt install zenity)"
