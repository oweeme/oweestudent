import base64
import sys
from pathlib import Path

import flet as ft


def _buscar(nombre: str):
    raiz = Path(__file__).resolve().parents[2]
    for base in (Path(getattr(sys, "_MEIPASS", raiz)), raiz, Path.cwd()):
        for sub in ("assets", "."):
            f = base / sub / nombre
            if f.exists():
                return f
    return None


def logo(tam: int = 96):
    """Logo de la app; si no se encuentra el archivo, usa un icono de respaldo."""
    f = _buscar("icon_256.png")
    if f:
        return ft.Image(src_base64=base64.b64encode(f.read_bytes()).decode(), width=tam, height=tam)
    return ft.Image(src="icon_256.png", width=tam, height=tam, error_content=ft.Text("🎓", size=tam * 0.6))
