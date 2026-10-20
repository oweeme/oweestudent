# Flatpak / Flathub (borrador, sin probar)

`app.oweestudent.OweeStudent.yml` reempaqueta el `.tar.gz` de una Release. Flathub prefiere compilar desde el código fuente,
y el cliente gráfico de Flet necesita `libmpv`, que el runtime de Freedesktop no incluye (hay que añadir un módulo `mpv`).
Antes de enviarlo a Flathub: completar el `sha256` de la Release, añadir ese módulo y probar con
`flatpak-builder --user --install --force-clean build packaging/flatpak/app.oweestudent.OweeStudent.yml`.
Mientras tanto, las vías probadas en Linux son el `.deb`, el `.tar.gz` con instalador de usuario y el `.AppImage`.
