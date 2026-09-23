#!/usr/bin/env python3
"""Hojas de personajes (fondo magenta) → un sprite PNG/WebP transparente por persona.

  uv run python scripts/escena/recortar.py <carpeta_hojas> web/gente
Cada hoja trae 8 personajes en 2 filas de 4; se detectan por componentes
conexas (no por cuadrícula fija) y se ordenan por fila y columna.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ALTO = 256          # alto final; se escala con vecino más cercano: el pixel queda nítido


def mascara(a):
    r, g, b = a[..., 0].astype(int), a[..., 1].astype(int), a[..., 2].astype(int)
    # magenta y sus bordes suavizados: rojo y azul altos, verde bajo
    return ~((r > 150) & (b > 150) & (g < 110) & (abs(r - b) < 90))


def componentes(m):
    """etiquetado 4-conexo por BFS sobre la máscara reducida (rápido y sin scipy)"""
    h, w = m.shape
    lab = np.zeros((h, w), int)
    cajas, n = [], 0
    for y0 in range(0, h, 2):
        for x0 in range(0, w, 2):
            if m[y0, x0] and not lab[y0, x0]:
                n += 1
                pila = [(y0, x0)]
                lab[y0, x0] = n
                x1 = x2 = x0
                y1 = y2 = y0
                c = 0
                while pila:
                    y, x = pila.pop()
                    c += 1
                    x1, x2, y1, y2 = min(x1, x), max(x2, x), min(y1, y), max(y2, y)
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        yy, xx = y + dy, x + dx
                        if 0 <= yy < h and 0 <= xx < w and m[yy, xx] and not lab[yy, xx]:
                            lab[yy, xx] = n
                            pila.append((yy, xx))
                if c > 400:
                    cajas.append([x1, y1, x2, y2, c])
    return cajas


def fusionar(cajas):
    """piezas sueltas (un micrófono, una canasta) se unen a la figura que las toca"""
    cajas = sorted(cajas, key=lambda c: -c[4])
    out = []
    for c in cajas:
        for o in out:
            if c[0] < o[2] + 12 and c[2] > o[0] - 12 and c[1] < o[3] + 12 and c[3] > o[1] - 12:
                o[0], o[1], o[2], o[3] = min(o[0], c[0]), min(o[1], c[1]), max(o[2], c[2]), max(o[3], c[3])
                o[4] += c[4]
                break
        else:
            out.append(list(c))
    return out


def main(hojas, salida):
    salida = Path(salida)
    salida.mkdir(parents=True, exist_ok=True)
    for hoja in sorted(Path(hojas).glob("*.png")):
        im = Image.open(hoja).convert("RGBA")
        a = np.array(im)
        m = mascara(a)
        cajas = fusionar(componentes(m))
        cajas = [c for c in cajas if (c[3] - c[1]) > 120][:8]
        filas = sorted(cajas, key=lambda c: c[1])
        corte = (filas[0][1] + filas[-1][1]) / 2
        orden = sorted(cajas, key=lambda c: (c[1] > corte, c[0]))
        a[..., 3] = np.where(m, 255, 0)
        for i, (x1, y1, x2, y2, _) in enumerate(orden):
            spr = Image.fromarray(a[y1:y2 + 1, x1:x2 + 1])
            esc = ALTO / spr.height
            spr = spr.resize((max(1, round(spr.width * esc)), ALTO), Image.NEAREST)
            base = salida / f"{hoja.stem}_{i}"
            spr.save(str(base) + ".webp", lossless=True)
        print(f"{hoja.stem}: {len(orden)} personajes")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
