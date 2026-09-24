#!/usr/bin/env python3
"""Quita el halo morado que deja el fondo magenta en el borde de los sprites.

El recorte (recortar.py) solo borra el magenta puro; los pixeles del borde, mezcla
de personaje y fondo, quedaban teñidos (144 de 153 hojas, ~50 % del contorno; en
algunos objetos, manchas anchas). Pixel a pixel desde lo transparente hacia adentro: si el pixel es casi el fondo, se
vuelve transparente; si solo está manchado, se le resta el magenta (rojo y azul
por encima del verde, parejos entre sí). Un rosado de verdad (rojo >> azul) no se toca.

  uv run python scripts/escena/limpiar_borde.py web/gente/*.webp
"""
import sys

import numpy as np
from PIL import Image

PASADAS = 40   # cada pasada avanza un pixel hacia adentro; para sola donde ya no hay magenta


def limpiar(im):
    a = np.array(im.convert("RGBA")).astype(int)
    tocado = np.zeros(a.shape[:2], bool)
    for k in range(PASADAS):
        op = a[..., 3] > 127
        frente = ~op | tocado          # se avanza desde lo transparente y desde lo ya limpiado
        cerca = np.zeros_like(op)
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)):
            cerca |= np.roll(np.roll(frente, dy, 0), dx, 1)
        cand = op & ~tocado & cerca
        r, g, b = a[..., 0], a[..., 1], a[..., 2]
        mancha = np.minimum(r, b) - g
        if k < 2:   # el anillo del borde: cualquier tinte magenta
            magenta = cand & (mancha > 12) & (np.abs(r - b) < 45)
        else:       # más adentro, solo magenta oscuro de verdad (un lila o un rosado de ropa no pasa)
            magenta = cand & (mancha > 20) & (np.abs(r - b) < 50) & (g < 120)
        fondo = magenta & (mancha > 70)
        a[..., 3][fondo] = 0
        sucio = magenta & ~fondo
        a[..., 0][sucio] -= mancha[sucio]
        a[..., 2][sucio] -= mancha[sucio]
        tocado |= sucio
        if not magenta.any():
            break
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGBA")


if __name__ == "__main__":
    for f in sys.argv[1:]:
        limpiar(Image.open(f)).save(f, "WEBP", lossless=True, method=6)
    print(f"{len(sys.argv) - 1} sprites limpios")
