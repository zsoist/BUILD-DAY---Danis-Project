#!/usr/bin/env python3
"""Hoja de GPT (3 filas = 3 personajes × 4 columnas: lado A, lado B, espalda A,
espalda B; fondo transparente) → tira de 8 cuadros por personaje:
  quieto, paso izq, paso der, mano arriba   (los 4 que ya había, de frente)
  lado A, lado B                            (camina a la derecha; a la izquierda se refleja)
  espalda A, espalda B                      (se aleja, hacia el fondo)

  uv run python scripts/escena/direcciones.py <hoja.png> id1 id2 id3

Los cuadros nuevos se escalan a la altura de la figura quieta (no a la de la
mano arriba) y se pegan con los pies abajo. Escribe web/gente/<id>_poses.webp
(8 cuadros). Al final, una sola vez (las hojas corren en paralelo):
  uv run python scripts/escena/direcciones.py --catalogo    # marca "d":8 en catalogo.json
Después cuantiza a 128 colores: GPT trae miles (las 144 tiras: 28 MB → 11 MB).
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from ambiente import componentes  # noqa: E402

GENTE = Path(__file__).resolve().parents[2] / "web" / "gente"


def caja(a):
    ys, xs = np.nonzero(a[..., 3] > 0)
    return xs.min(), ys.min(), xs.max(), ys.max()


def main(hoja, ids):
    a = np.asarray(Image.open(hoja).convert("RGBA")).copy()
    m = a[..., 3] > 200
    a[..., 3] = np.where(m, 255, 0)
    H, W = m.shape
    filas = len(ids)
    celdas = {}
    for x1, y1, x2, y2, n in componentes(m):
        if n < 60:
            continue
        k = (min(filas - 1, int((y1 + y2) / 2 / (H / filas))), min(3, int((x1 + x2) / 2 / (W / 4))))
        celdas.setdefault(k, []).append((n, x1, y1, x2, y2))
    for f, pid in enumerate(ids):
        tira = Image.open(GENTE / f"{pid}_poses.webp").convert("RGBA")
        if tira.width / tira.height > 3.6:                  # ya tiene 8 cuadros: no se rehace
            print("  ya estaba", pid); continue
        cw = tira.width // 4
        viejos = [tira.crop((i * cw, 0, (i + 1) * cw, tira.height)) for i in range(4)]
        x1, y1, x2, y2 = caja(np.asarray(viejos[0]))
        alto = y2 - y1 + 1                                   # la figura quieta, sin la mano arriba
        nuevos = []
        for col in range(4):
            piezas = sorted(celdas.get((f, col), []), reverse=True)
            if not piezas:
                print("  falta", pid, col); break
            _, x1, y1, x2, y2 = piezas[0]
            for _, b1, c1, b2, c2 in piezas[1:]:           # lo que carga (canasta, lazo) si cae encima
                if b2 >= x1 and b1 <= x2:
                    x1, y1, x2, y2 = min(x1, b1), min(y1, c1), max(x2, b2), max(y2, c2)
            p = Image.fromarray(a[y1:y2 + 1, x1:x2 + 1])
            e = alto / p.height
            nuevos.append(p.resize((max(1, round(p.width * e)), alto), Image.NEAREST))
        if len(nuevos) < 4:
            continue
        ancho = max(cw, *(n.width for n in nuevos))
        out = Image.new("RGBA", (ancho * 8, tira.height), (0, 0, 0, 0))
        for i, v in enumerate(viejos):
            out.alpha_composite(v, (i * ancho + (ancho - cw) // 2, 0))
        for i, n in enumerate(nuevos):
            out.alpha_composite(n, ((4 + i) * ancho + (ancho - n.width) // 2, tira.height - 1 - n.height - (tira.height - 1 - caja(np.asarray(viejos[0]))[3])))
        out.save(GENTE / f"{pid}_poses.webp", lossless=True)
        print(f"  {pid}: 8 cuadros de {ancho}px")


def catalogo():
    f = GENTE / "catalogo.json"
    c = json.loads(f.read_text())
    n = 0
    for g in c["gente"]:
        t = Image.open(GENTE / f"{g['id']}_poses.webp")
        if t.width / t.height > 3.6:
            g["d"] = 8; n += 1
        else:
            g.pop("d", None)
    f.write_text(json.dumps(c, ensure_ascii=False, separators=(",", ":")))
    print(f"{n}/{len(c['gente'])} con 8 cuadros")


if __name__ == "__main__":
    if sys.argv[1] == "--catalogo":
        catalogo()
    else:
        main(sys.argv[1], sys.argv[2:])
