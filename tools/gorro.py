"""Genera assets/icon.png: el logo de Oweeme con un gorro de graduación sobre el pez. (Herramienta de diseño, no es parte de la app.)"""
from PIL import Image, ImageDraw

S = 4  # supersampling


def gorro(ancho: int) -> Image.Image:
    W = ancho * S
    H = int(W * 0.46)
    lienzo = Image.new("RGBA", (W, int(W * 0.9)), (0, 0, 0, 0))
    d = ImageDraw.Draw(lienzo)
    cx, cy = W // 2, int(W * 0.30)
    oscuro, borde, crema, coral = (43, 38, 40, 255), (253, 235, 170, 255), (253, 235, 170, 255), (255, 94, 71, 255)
    # base (parte que abraza la cabeza), debajo del tablero
    bw, bh = int(W * 0.30), int(H * 0.62)
    d.rectangle([cx - bw, cy, cx + bw, cy + bh], fill=(30, 27, 29, 255))
    d.ellipse([cx - bw, cy + bh - int(H * 0.22), cx + bw, cy + bh + int(H * 0.22)], fill=(30, 27, 29, 255))
    # tablero (rombo plano)
    rombo = [(cx - W // 2, cy), (cx, cy - H // 2), (cx + W // 2, cy), (cx, cy + H // 2)]
    d.polygon(rombo, fill=oscuro)
    d.line(rombo + [rombo[0]], fill=borde, width=int(W * 0.012), joint="curve")
    # botón central y cordón con borla
    r = int(W * 0.03)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=crema)
    fx, fy = cx + int(W * 0.36), cy + int(H * 0.06)
    d.line([(cx, cy), (fx, fy)], fill=coral, width=int(W * 0.022))
    d.line([(fx, fy), (fx + int(W * 0.01), fy + int(H * 0.78))], fill=coral, width=int(W * 0.022))
    tw = int(W * 0.05)
    d.rounded_rectangle([fx - tw + int(W * 0.01), fy + int(H * 0.70), fx + tw + int(W * 0.01), fy + int(H * 1.12)],
                        radius=int(W * 0.02), fill=coral)
    return lienzo


def construir(origen: str, salida: str, tam=1024, ancho_gorro=360, pos=(250, 420), angulo=22):
    logo = Image.open(origen).convert("RGBA").resize((tam, tam), Image.LANCZOS)
    g = gorro(ancho_gorro).transpose(Image.FLIP_LEFT_RIGHT).rotate(angulo, resample=Image.BICUBIC, expand=True)
    g = g.resize((g.width // S, g.height // S), Image.LANCZOS)
    logo.alpha_composite(g, (pos[0] - g.width // 2, pos[1] - g.height // 2))
    logo.save(salida)
    return logo


if __name__ == "__main__":
    import sys
    construir("tools/logo_original.png", "assets/icon.png", ancho_gorro=330, pos=(262, 540), angulo=22)
