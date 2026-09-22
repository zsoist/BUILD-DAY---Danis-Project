#!/usr/bin/env python3
"""¿Cuánto dicen "sí" las voces, contra cuánto dicen "sí" los colombianos?

Para preguntas de acuerdo de la ECP 2023 (P5261S1..S8: Sí / No / No sabe), que
tienen la forma de lo que hace el sitio: una proposición y una postura.

Compara, sobre el mismo ítem, archivos de careo_ecp.mjs en cualquier modo:
  categórico → la voz escoge 1 (sí), 2 (no) o 99 (no sabe)
  libre      → la voz habla; la postura sale por SSR contra cuatro anclas
               (sí · no · depende · no sé), guardando la distribución entera

Dos juegos de anclas, porque los embeddings manejan mal la negación ("estoy de
acuerdo" y "no estoy de acuerdo" quedan muy cerca):
  genéricas     polaridad con vocabulario distinto (apoyo / rechazo)
  proposición   las mismas, pero nombrando la proposición

  uv run python scripts/experimento/postura.py a.json [b.json ...]
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import careo_ecp as C  # noqa: E402  la verdad del DANE, ponderada
import ssr as S        # noqa: E402  embeddings, coseno, pmf

import os
# T del softmax. 0.25 viene del paper (termómetros); para posturas se calibra
# aparte y se prueba en ítems que no se usaron para calibrar.
TEMP = float(os.environ.get("SSR_TEMP", "0.25"))

GENERICAS = [
    "Sí, claro que estoy de acuerdo con eso. Me parece bien y lo apoyo.",
    "No, eso me parece mal. Lo rechazo, no lo apoyo para nada.",
    "Depende. Tiene su lado bueno y su lado malo, no es tan sencillo.",
    "No sé, la verdad eso no lo he pensado y no tengo opinión.",
]


def proposicion(texto):
    t = texto.strip("¿? ")
    i = t.lower().find(" con que ")
    return t[i + len(" con que "):] if i >= 0 else t


def de_proposicion(prop):
    return [f"Estoy de acuerdo con que {prop}. Lo apoyo.",
            f"Rechazo que {prop}. Eso está mal.",
            f"Sobre que {prop}: depende, tiene su lado bueno y su lado malo.",
            f"Sobre que {prop} no tengo opinión, no sé."]


_HUM = {}


def humano(codigo):
    """% sí entre quienes contestan sí o no, y % no sabe; ponderado FEX."""
    if codigo in _HUM:
        return _HUM[codigo]
    demo = C.cargar("ecp2023_democracia.zip")
    viv = C.cargar("ecp2023_viviendas.zip")
    fex = next(c for c in viv.columns if c.upper().startswith("FEX"))
    demo = demo.merge(viv[["DIRECTORIO", fex]].drop_duplicates("DIRECTORIO"),
                      on="DIRECTORIO", how="left")
    si = no = ns = 0.0
    for v, w in zip(demo[codigo].tolist(), demo[fex].fillna(0).tolist()):
        if v == 1:
            si += w
        elif v == 2:
            no += w
        elif v == 99:
            ns += w
    _HUM[codigo] = (si / (si + no), ns / (si + no + ns))
    return _HUM[codigo]


def por_ssr(textos, anclas):
    vecs = S.embeber(anclas + textos)
    va, vr = vecs[:4], vecs[4:]
    suave = [0.0] * 4
    duro = [0] * 4
    for v in vr:
        p = S.pmf_de([S.coseno(v, a) for a in va], TEMP)
        for k in range(4):
            suave[k] += p[k]
        duro[p.index(max(p))] += 1
    si_s, no_s = suave[0], suave[1]
    si_d, no_d = duro[0], duro[1]
    n = len(vr)
    return ((si_s / (si_s + no_s)), (suave[2] + suave[3]) / n,
            (si_d / (si_d + no_d) if si_d + no_d else float("nan")))


def main():
    filas = []
    for ruta in sys.argv[1:]:
        D = json.loads(Path(ruta).read_text())
        cod, modo = D["codigo"], D.get("modo", "categorico")
        lib = "con" if D.get("libreto", True) else "sin"
        h_si, h_ns = humano(cod)
        if modo == "libre":
            textos = [(r.get("crudo") or "").strip() for r in D["respuestas"]]
            textos = [x for x in textos if len(x) >= 8]
            prop = proposicion(D.get("pregunta_libre") or D["pregunta"].split("?")[0])
            g_si, g_ind, g_arg = por_ssr(textos, GENERICAS)
            p_si, p_ind, p_arg = por_ssr(textos, de_proposicion(prop))
            filas.append((cod, lib, "SSR genéricas", h_si, g_si, g_ind))
            filas.append((cod, lib, "SSR proposición", h_si, p_si, p_ind))
            filas.append((cod, lib, "argmax proposición", h_si, p_arg, None))
        else:
            v = [r.get("resp") for r in D["respuestas"]]
            si, no, ns = v.count(1), v.count(2), v.count(99)
            filas.append((cod, lib, "categórico", h_si,
                          si / (si + no) if si + no else float("nan"),
                          ns / len(v) if v else None))

    print(f"\n{'ítem':<9}{'libreto':<9}{'método':<20}{'humano':>8}{'voces':>8}{'error':>8}{'indeciso':>10}")
    print("-" * 72)
    err = {}
    for cod, lib, met, h, s, ind in filas:
        e = abs(s - h) * 100
        err.setdefault((lib, met), []).append(e)
        print(f"{cod:<9}{lib:<9}{met:<20}{100*h:>7.1f}%{100*s:>7.1f}%{e:>7.1f}"
              + (f"{100*ind:>9.1f}%" if ind is not None else ""))
    print("-" * 72)
    print("error medio (puntos de % sí):")
    for (lib, met), es in sorted(err.items(), key=lambda x: sum(x[1]) / len(x[1])):
        print(f"  {lib:<4} libreto · {met:<20} {sum(es)/len(es):5.1f}   (n={len(es)} ítems)")


if __name__ == "__main__":
    main()
