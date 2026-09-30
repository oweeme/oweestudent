"""Extracción de URLs, libros y recursos desde texto libre."""
import re

_URL = re.compile(r'https?://[^\s<>")\]]+|www\.[^\s<>")\]]+')
_DOMINIO = re.compile(r'\b[\w-]+(?:\.[\w-]+)*\.(?:com|org|net|edu|io|online)\b', re.I)
_LIBRO = re.compile(r'\*([^*\n]{6,120})\*\s*[–—-]\s*([^\n.]+)')  # *Título* – Autor


def extraer_urls(texto: str) -> list[str]:
    return sorted({u.rstrip(".,;") for u in _URL.findall(texto)})


def extraer_dominios(texto: str) -> list[str]:
    return sorted({d.lower() for d in _DOMINIO.findall(texto)})


def extraer_libros(texto: str) -> list[tuple[str, str]]:
    """Devuelve [(titulo, autor)] para el patrón *Título* – Autor."""
    vistos, out = set(), []
    for t, a in _LIBRO.findall(texto):
        k = t.strip().lower()
        if k not in vistos:
            vistos.add(k)
            out.append((t.strip(), a.strip()))
    return out
