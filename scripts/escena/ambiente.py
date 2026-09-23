#!/usr/bin/env python3
"""Hoja de ambiente de GPT Image (fondo transparente, 4×3) → web/escenas/amb/<id>.webp

  uv run python scripts/escena/ambiente.py <hoja.png> id1 id2 ... id12

GPT deja un resplandor semitransparente alrededor de cada pieza (alfa < 30) y
la pieza a alfa ~250: se corta en alfa > 200 y se deja opaca. Por casilla se
queda la pieza más grande y lo que cae encima o debajo de ella (la batea de
frutas sobre la cabeza, el parasol del carrito).
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

SAL = Path(__file__).resolve().parents[2] / "web" / "escenas" / "amb"


def componentes(m):
    H, W = m.shape
    visto = np.zeros_like(m)
    out = []
    for y0, x0 in zip(*np.nonzero(m)):
        if visto[y0, x0]:
            continue
        pila, x1, y1, x2, y2, n = [(y0, x0)], x0, y0, x0, y0, 0
        visto[y0, x0] = True
        while pila:
            y, x = pila.pop(); n += 1
            x1, y1, x2, y2 = min(x1, x), min(y1, y), max(x2, x), max(y2, y)
            for v, u in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                if 0 <= v < H and 0 <= u < W and m[v, u] and not visto[v, u]:
                    visto[v, u] = True; pila.append((v, u))
        out.append((x1, y1, x2, y2, n))
    return out


def main(hoja, ids):
    SAL.mkdir(parents=True, exist_ok=True)
    a = np.asarray(Image.open(hoja).convert("RGBA")).copy()
    m = a[..., 3] > 200
    H, W = m.shape
    celdas = {}
    for x1, y1, x2, y2, n in componentes(m):
        if n < 40:
            continue
        k = (min(2, int((y1 + y2) / 2 / (H / 3))), min(3, int((x1 + x2) / 2 / (W / 4))))
        celdas.setdefault(k, []).append((n, x1, y1, x2, y2))
    a[..., 3] = np.where(m, 255, 0)
    for i, pid in enumerate(ids):
        piezas = sorted(celdas.get((i // 4, i % 4), []), reverse=True)
        if not piezas:
            print("  falta", pid); continue
        _, x1, y1, x2, y2 = piezas[0]
        for _, a1, b1, a2, b2 in piezas[1:]:
            if a2 >= x1 and a1 <= x2:
                x1, y1, x2, y2 = min(x1, a1), min(y1, b1), max(x2, a2), max(y2, b2)
        Image.fromarray(a[y1:y2 + 1, x1:x2 + 1]).save(SAL / f"{pid}.webp", lossless=True)
        print(f"  {pid}: {x2 - x1 + 1}×{y2 - y1 + 1}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
