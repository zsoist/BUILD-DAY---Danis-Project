#!/usr/bin/env python3
"""Hojas de poses (fondo magenta, filas × 4 poses) → por personaje:
  <id>.webp        la pose quieta (retrato del chat y respaldo)
  <id>_poses.webp  tira de 4 cuadros iguales: quieto, paso izq, paso der, mano arriba

  uv run python scripts/escena/recortar_poses.py <hoja.png> <salida> <id_fila1> [<id_fila2> ...]
Cada pieza cae en su casilla por su centro (una canasta suelta se une a su
dueño), así que no hace falta que el modelo respete márgenes exactos.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from recortar import ALTO, componentes, mascara  # noqa: E402
from limpiar_borde import limpiar  # noqa: E402   (sin él queda un halo morado)


def main(hoja, salida, ids):
    salida = Path(salida)
    salida.mkdir(parents=True, exist_ok=True)
    im = Image.open(hoja).convert("RGBA")
    a = np.array(im)
    m = mascara(a)
    H, W = m.shape
    filas = len(ids)
    # por casilla: la figura principal (la pieza más grande) y solo las piezas
    # que caen sobre ella (lo que carga en la mano); una figura vecina que se
    # coló en la casilla se descarta
    porcasilla = {}
    for x1, y1, x2, y2, n in componentes(m):
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        k = (min(filas - 1, int(cy / (H / filas))), min(3, int(cx / (W / 4))))
        porcasilla.setdefault(k, []).append((n, x1, y1, x2, y2))
    celdas = {}
    for k, piezas in porcasilla.items():
        piezas.sort(reverse=True)
        _, x1, y1, x2, y2 = piezas[0]
        margen = (x2 - x1) * .25
        c = [x1, y1, x2, y2]
        for _, a1, b1, a2, b2 in piezas[1:]:
            if a2 >= x1 - margen and a1 <= x2 + margen:
                c = [min(c[0], a1), min(c[1], b1), max(c[2], a2), max(c[3], b2)]
        celdas[k] = c
    a[..., 3] = np.where(m, 255, 0)
    for f, pid in enumerate(ids):
        cuadros = []
        for col in range(4):
            if (f, col) not in celdas:
                print(f"  {pid}: falta la pose {col + 1}; se usa la quieta")
                continue
            x1, y1, x2, y2 = celdas[(f, col)]
            cuadros.append((col, Image.fromarray(a[y1:y2 + 1, x1:x2 + 1])))
        if not cuadros:
            print(f"  {pid}: sin poses")
            continue
        # misma escala para los 4: la del más alto (los pasos no deben encoger)
        alto = max(c.height for _, c in cuadros)
        esc = ALTO / alto
        cuadros = {col: c.resize((max(1, round(c.width * esc)), max(1, round(c.height * esc))), Image.NEAREST)
                   for col, c in cuadros}
        quieto = cuadros.get(0) or next(iter(cuadros.values()))
        ancho = max(c.width for c in cuadros.values())
        tira = Image.new("RGBA", (ancho * 4, ALTO), (0, 0, 0, 0))
        for col in range(4):
            c = cuadros.get(col, quieto)
            tira.alpha_composite(c, (col * ancho + (ancho - c.width) // 2, ALTO - c.height))   # pies abajo
        limpiar(tira).save(salida / f"{pid}_poses.webp", lossless=True)
        limpiar(quieto).save(salida / f"{pid}.webp", lossless=True)
        print(f"  {pid}: {len(cuadros)} poses")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
