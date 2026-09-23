#!/usr/bin/env python3
"""Recorta el cielo de cada fondo para que el sitio pinte uno vivo detrás
(nubes que pasan, pájaros). Deja web/escenas/<k>_tierra.webp (el fondo con el
cielo transparente) y web/escenas/cielos.json (los colores del cielo original,
para que el cielo nuevo case con la luz de la escena y no quede halo).

  uv run python scripts/escena/cielo.py            # todos los de TECHO
  uv run python scripts/escena/cielo.py --ver out.png   # hoja de control (magenta = cielo)

Relleno desde el borde de arriba por píxeles claros y parecidos a su vecino,
nunca por debajo del techo de cada escena: el río del Atrato o la arena de la
Guajira son tan claros como el cielo y sin techo se los come.
"""
import json
import sys
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

ESC = Path(__file__).resolve().parents[2] / "web" / "escenas"
# techo = fracción de la altura hasta donde puede llegar el cielo (medido a ojo en la hoja de control)
TECHO = {"nacional": .21, "bogota": .5, "medellin": .24, "caribe": .35, "cafetero": .45, "llanos": .5,
         "amazonia": .40, "choco": .44, "santander": .5, "narino": .3, "popayan": .45, "cali": .45,
         "guajira": .33, "sanandres": .22}
# panorámicas (<k>_pano.webp, 2048×896, para más de 9 personas): otro encuadre, otro techo
TECHO.update({"nacional_pano": .3, "bogota_pano": .45, "medellin_pano": .2, "caribe_pano": .3, "cafetero_pano": .35,
              "llanos_pano": .45, "amazonia_pano": .25, "choco_pano": .15, "santander_pano": .3, "popayan_pano": .3,
              "cali_pano": .35, "guajira_pano": .12, "sanandres_pano": .15})
# tatacoa (noche con vía láctea) y boyaca (cielo azul con montañas) ya tienen cielo vivo: se dejan
TOL = {"nacional": 10, "bogota": 11, "santander": 10, "nacional_pano": 10, "bogota_pano": 11, "popayan_pano": 24}     # neblina lejana casi del color del cielo: tolerancia corta
LUZ = {"cafetero_pano": 45, "popayan_pano": 0}   # cenit oscuro: sin esto queda una nube negra
HORA = {"llanos": "tarde", "caribe": "tarde", "llanos_pano": "tarde", "caribe_pano": "tarde", "cali_pano": "tarde",
        "amazonia_pano": "bruma", "choco_pano": "bruma", "narino": "niebla", "amazonia": "bruma", "choco": "bruma"}


def mascara(a, techo, tol=16, luz=95):
    H, W, _ = a.shape
    lum = a.mean(2)
    cielo = np.zeros((H, W), bool)
    q = deque()
    for x in range(W):
        if lum[0, x] > luz + 15:
            cielo[0, x] = True
            q.append((0, x))
    lim = int(H * techo)
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            v, u = y + dy, x + dx
            if 0 <= v < lim and 0 <= u < W and not cielo[v, u] \
                    and np.abs(a[v, u] - a[y, x]).sum() < tol and lum[v, u] > luz:
                cielo[v, u] = True
                q.append((v, u))
    return cielo


def sin_islas(m, lim, maxarea=900):
    """Pedacitos de hoja o de neblina que quedaron flotando dentro del cielo: se vuelven cielo.
    Una isla es lo no-cielo que no toca el techo ni los bordes y es chica (la bandera no lo es)."""
    H, W = m.shape
    visto = m.copy()
    for y0 in range(lim):
        for x0 in range(W):
            if visto[y0, x0]:
                continue
            pila, comp, toca = [(y0, x0)], [], False
            visto[y0, x0] = True
            while pila:
                y, x = pila.pop()
                comp.append((y, x))
                if y >= lim - 1 or x in (0, W - 1):
                    toca = True
                for v, u in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                    if 0 <= v < lim and 0 <= u < W and not visto[v, u]:
                        visto[v, u] = True
                        pila.append((v, u))
            if not toca and len(comp) <= maxarea:
                for y, x in comp:
                    m[y, x] = True
    return m


def main():
    ver = sys.argv[sys.argv.index("--ver") + 1] if "--ver" in sys.argv else None
    datos, hojas = {}, []
    for k, techo in TECHO.items():
        im = Image.open(ESC / f"{k}.webp").convert("RGBA")
        a = np.asarray(im.convert("RGB")).astype(int)
        m = mascara(a, techo, TOL.get(k, 16), LUZ.get(k, 95))
        # come 1 px del borde claro (el halo del cielo viejo pegado a los tejados)
        m = np.asarray(Image.fromarray(m.astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(3))) > 127
        m &= np.arange(a.shape[0])[:, None] < int(a.shape[0] * techo)
        m = sin_islas(m, int(a.shape[0] * techo))
        if m.mean() < .02:                 # cielo oscuro o sin cielo: se deja como está
            (ESC / f"{k}_tierra.webp").unlink(missing_ok=True)
            print(k, "sin cielo recortable")
            continue
        rgba = np.asarray(im).copy()
        rgba[..., 3] = np.where(m, 0, 255)
        Image.fromarray(rgba).save(ESC / f"{k}_tierra.webp", lossless=False, quality=90, method=6)
        ys = np.nonzero(m.any(1))[0]
        arriba = a[:max(1, int(len(ys) * .25))][m[:max(1, int(len(ys) * .25))]]
        abajo = a[ys[-1] - max(1, len(ys) // 5):ys[-1] + 1][m[ys[-1] - max(1, len(ys) // 5):ys[-1] + 1]] if len(ys) else arriba
        hexa = lambda c: "#%02x%02x%02x" % tuple(int(v) for v in np.median(c, 0)) if len(c) else "#9ec5ff"
        datos[k] = {"arriba": hexa(arriba), "abajo": hexa(abajo), "horizonte": round((ys[-1] + 1) / a.shape[0], 3) if len(ys) else 0,
                    "hora": HORA.get(k, "dia"), "cubre": round(float(m.mean()), 3)}
        print(k, datos[k])
        if ver:
            v = a.copy(); v[m] = [255, 0, 255]
            hojas.append(Image.fromarray(v.astype("uint8")).resize((344, 192), Image.NEAREST))
    (ESC / "cielos.json").write_text(json.dumps(datos, ensure_ascii=False, separators=(",", ":")))
    if ver:
        W = Image.new("RGB", (344 * 3, 192 * ((len(hojas) + 2) // 3)))
        for i, h in enumerate(hojas):
            W.paste(h, ((i % 3) * 344, (i // 3) * 192))
        W.save(ver)


if __name__ == "__main__":
    main()
