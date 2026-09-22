#!/usr/bin/env python3
"""Valida la abstención calibrada contra la ECP 2023 del DANE.

Responde tres preguntas, en orden de importancia:
  (a) ¿La tasa de "no sé" se parece a la humana, global y por educación?
  (b) ¿Se degradó la distribución de los que SÍ contestaron? (sobreabstención)
  (c) ¿Mejoró la razón de desviación estándar?

La tercera es la interesante: la teoría dice que "no sé" y el punto medio
compiten por la misma masa, así que calibrar la abstención debería ensanchar
la dispersión de los que responden.

  uv run --with pyreadstat --with pandas --python 3.12 python \
     scripts/experimento/abstencion_valida.py <archivo_abstencion_gen.json>
"""
import json
import math
import os
import sys
import tempfile
import zipfile
from pathlib import Path

import pyreadstat

sys.path.insert(0, str(Path(__file__).resolve().parent))
import abstencion as A  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
RAW = RAIZ / "simcolombia" / "data" / "raw_v2"
NS = 99
TMP = tempfile.mkdtemp()
LLAVES = ["DIRECTORIO", "NRO_ENCUESTA", "HOGAR_NUMERO", "PERSONA_NUMERO"]


def cargar(z):
    with zipfile.ZipFile(RAW / z) as f:
        sav = next(n for n in f.namelist() if n.endswith(".sav"))
        f.extract(sav, TMP)
    return pyreadstat.read_sav(os.path.join(TMP, sav))[0]


def dist(valores, pesos=None):
    """Proporciones 1..5 (excluye el 'no sé') y tasa de 'no sé'."""
    c = {k: 0.0 for k in range(1, 6)}
    tot = ns = n = 0.0
    for i, v in enumerate(valores):
        if v is None or v != v:
            continue
        w = 1.0 if pesos is None else float(pesos[i])
        n += w
        if int(v) == NS:
            ns += w
        elif int(v) in c:
            c[int(v)] += w
            tot += w
    return ({k: (v / tot if tot else 0.0) for k, v in c.items()},
            ns / n if n else 0.0)


def w1(p, q):
    ap = aq = acc = 0.0
    for i in range(1, 5):
        ap += p[i]
        aq += q[i]
        acc += abs(ap - aq)
    return acc / 4


def media_sd(p):
    mu = sum(k * v for k, v in p.items())
    return mu, math.sqrt(sum(v * (k - mu) ** 2 for k, v in p.items()))


def fila(nombre, p, ns, ref=None):
    mu, sd = media_sd(p)
    r = f"{nombre:<22}" + "".join(f"{100*p[k]:>7.1f}" for k in range(1, 6))
    r += f"{mu:>8.2f}{sd:>8.2f}{100*ns:>8.1f}%"
    if ref:
        r += f"{w1(p, ref):>9.3f}"
    return r


def main():
    D = json.loads(Path(sys.argv[1]).read_text())
    res = D["respuestas"]
    codigo = D["codigo"]

    # ── humanos (ponderados con el factor de expansión oficial) ──────────
    demo = cargar("ecp2023_democracia.zip")
    try:
        viv = cargar("ecp2023_viviendas.zip")
        fex = next((c for c in viv.columns if c.upper().startswith("FEX")), None)
    except Exception:
        viv, fex = None, None
    if fex:
        demo = demo.merge(viv[["DIRECTORIO", fex]].drop_duplicates("DIRECTORIO"),
                          on="DIRECTORIO", how="left")
        pesos = demo[fex].fillna(0).tolist()
    else:
        pesos = None
    p_hum, ns_hum = dist(demo[codigo].tolist(), pesos)

    # tasa humana de "no sé" por educación (P6210 del módulo de características)
    car = cargar("ecp2023_caracteristicas.zip")
    mh = demo.merge(car[LLAVES + ["P6210", "P5785"]], on=LLAVES, how="inner")
    mh = mh[mh["P5785"] >= 18]
    ns_hum_edu = {}
    for g, lo, hi in (("bajo", 1, 3), ("medio", 4, 4), ("alto", 5, 7)):
        sub = mh[(mh["P6210"] >= lo) & (mh["P6210"] <= hi)][codigo].dropna()
        if len(sub):
            ns_hum_edu[g] = sum(1 for v in sub if v == NS) / len(sub)

    # ── sintéticos: antes y después ──────────────────────────────────────
    escala = A.escala_de_item(sum(x["score"] for x in res) / len(res))
    con = A.aplicar([dict(x) for x in res], escala)
    p_antes, ns_antes = dist([x["moda"] for x in res])
    p_desp, ns_desp = dist([x.get("final", x["moda"]) for x in con])

    print(f"\nABSTENCIÓN CALIBRADA — {codigo} · K={D.get('k')} · n={len(res)}")
    print(f"escala de dificultad estimada del ítem: {escala:.2f}\n")
    cab = f"{'':<22}" + "".join(f"{k:>7}" for k in range(1, 6))
    print(cab + f"{'media':>8}{'desv':>8}{'no sé':>9}{'W1':>9}")
    print("-" * 81)
    print(fila("humanos (ECP)", p_hum, ns_hum))
    print(fila("sintético ANTES", p_antes, ns_antes, p_hum))
    print(fila("sintético DESPUÉS", p_desp, ns_desp, p_hum))
    print("-" * 81)

    # ── (a) tasa de 'no sé' ──────────────────────────────────────────────
    print("\n(a) TASA DE «NO SÉ»")
    print(f"    global   humano {100*ns_hum:.1f}%  ·  antes {100*ns_antes:.1f}%  "
          f"·  después {100*ns_desp:.1f}%")
    brecha_a = abs(ns_antes - ns_hum) * 100
    brecha_d = abs(ns_desp - ns_hum) * 100
    print(f"    brecha en puntos: {brecha_a:.1f} → {brecha_d:.1f}")
    print("    por educación (solo sintético, contra el humano):")
    cel = {}
    for x in con:
        g = A.grupo_educacion(x.get("educacion"))
        cel.setdefault(g, []).append(1 if x.get("final") == NS else 0)
    for g in ("bajo", "medio", "alto"):
        if g in cel and cel[g]:
            obs = 100 * sum(cel[g]) / len(cel[g])
            hum = 100 * ns_hum_edu.get(g, float("nan"))
            print(f"      {g:<6} n={len(cel[g]):>4}   sintético {obs:5.1f}%   humano {hum:5.1f}%")

    # ── (b) sobreabstención ──────────────────────────────────────────────
    w_a, w_d = w1(p_antes, p_hum), w1(p_desp, p_hum)
    print("\n(b) LOS QUE SÍ CONTESTARON (riesgo de sobreabstención)")
    print(f"    W1 antes {w_a:.3f} → después {w_d:.3f}   "
          f"({'no se degradó' if w_d <= w_a + 0.005 else 'SE DEGRADÓ'})")

    # ── (c) dispersión ───────────────────────────────────────────────────
    _, sd_h = media_sd(p_hum)
    _, sd_a = media_sd(p_antes)
    _, sd_d = media_sd(p_desp)
    print("\n(c) DISPERSIÓN (objetivo: razón 1.00)")
    print(f"    razón antes {sd_a/sd_h:.2f} → después {sd_d/sd_h:.2f}")

    print("\nVEREDICTO")
    va = "MEJORA" if brecha_d < brecha_a - 0.2 else ("EMPATE" if abs(brecha_d - brecha_a) <= 0.2 else "EMPEORA")
    vb = "MEJORA" if w_d < w_a - 0.005 else ("EMPATE" if w_d <= w_a + 0.005 else "EMPEORA")
    vc = "MEJORA" if abs(sd_d/sd_h - 1) < abs(sd_a/sd_h - 1) - 0.01 else (
        "EMPATE" if abs(abs(sd_d/sd_h - 1) - abs(sd_a/sd_h - 1)) <= 0.01 else "EMPEORA")
    print(f"  (a) tasa de «no sé» ................ {va}")
    print(f"  (b) distribución de los que contestan {vb}")
    print(f"  (c) razón de desviación ............ {vc}")


if __name__ == "__main__":
    main()
