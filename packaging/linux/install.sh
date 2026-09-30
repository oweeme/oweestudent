#!/usr/bin/env bash
# Instala OweeStudent SOLO para tu usuario (~/.local). No necesita sudo.
set -euo pipefail
AQUI="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/.local/opt/oweestudent"
BIN="$HOME/.local/bin"
APPS="$HOME/.local/share/applications"
LIBS="$HOME/.local/lib/oweestudent"

mkdir -p "$DEST" "$BIN" "$APPS" "$LIBS"
rm -rf "$DEST"/*
cp -r "$AQUI/app/." "$DEST/"
[ -f "$AQUI/oweestudent.png" ] && cp "$AQUI/oweestudent.png" "$DEST/oweestudent.png" || true

# Flet necesita libmpv.so.1; muchas distribuciones nuevas solo traen libmpv.so.2 (compatible para nuestro uso)
NEEDS_LIBS=0
if ! ldconfig -p 2>/dev/null | grep -q "libmpv.so.1"; then
  MPV2="$(ldconfig -p 2>/dev/null | awk '/libmpv.so.2/{print $NF; exit}')"
  if [ -n "$MPV2" ]; then ln -sf "$MPV2" "$LIBS/libmpv.so.1"; NEEDS_LIBS=1
  else echo "Aviso: no encuentro libmpv. Instálala una vez con:  sudo apt install libmpv2   (o el equivalente de tu distro)"; fi
fi

cat > "$BIN/oweestudent" <<WRAP
#!/usr/bin/env bash
$( [ "$NEEDS_LIBS" = 1 ] && echo "export LD_LIBRARY_PATH=\"$LIBS\${LD_LIBRARY_PATH:+:\$LD_LIBRARY_PATH}\"" )
exec "$DEST/OweeStudent" "\$@"
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
command -v zenity >/dev/null || echo "   Consejo: instala 'zenity' para el selector de archivos (sudo apt install zenity)"
