#!/usr/bin/env bash
# Quita el programa. Tus estudios (~/.oweestudent) NO se borran.
rm -rf "$HOME/.local/opt/oweestudent" "$HOME/.local/lib/oweestudent" \
       "$HOME/.local/bin/oweestudent" "$HOME/.local/share/applications/oweestudent.desktop"
echo "Desinstalado. Tus datos siguen en ~/.oweestudent (bórralos a mano si quieres)."
