#!/usr/bin/env python3
"""Compara la distribución de respuestas SINTÉTICAS contra la HUMANA REAL de la
Encuesta de Cultura Política del DANE, sobre la misma pregunta literal.

Métricas (las que pide la literatura, calculadas en Python, sin LLM de por medio):
  · W1 normalizado  — distancia de Wasserstein sobre la escala ordinal, ÷ (K-1).
                      Respeta el orden: confundir 4 con 5 pesa menos que 1 con 5.
  · razón de SD     — dispersión sintética ÷ humana. El fallo documentado de los
                      modelos es la SUB-DISPERSIÓN: todos opinan parecido.
                      Objetivo = 1.0.
  · tasa de "no sé" — los modelos producen muy pocas; los humanos, muchas.

Uso:
  uv run --with pyreadstat --with pandas --python 3.12 python \
     scripts/experimento/careo_ecp.py <archivo_careo.json>
"""
import json
import math
import os
import sys
import tempfile
import zipfile
from pathlib import Path

import pyreadstat

RAIZ = Path(__file__).resolve().parents[2]
RAW = RAIZ / "simcolombia" / "data" / "raw_v2"
LLAVES = ["DIRECTORIO", "NRO_ENCUESTA", "HOGAR_NUMERO", "PERSONA_NUMERO"]
NS = 99                      # código de "no sabe / no informa" del DANE
TMP = tempfile.mkdtemp()


def cargar(zip_nombre):
    with zipfile.ZipFile(RAW / zip_nombre) as z:
        sav = next(n for n in z.namelist() if n.endswith(".sav"))
        z.extract(sav, TMP)
    return pyreadstat.read_sav(os.path.join(TMP, sav))[0]


def distribucion(valores, pesos=None):
    """Proporciones sobre 1..5, descartando el 'no sé'."""
    tot = 0.0
    d = {k: 0.0 for k in range(1, 6)}
    for i, v in enumerate(valores):
        if v is None or v != v or int(v) not in d:
            continue
        w = 1.0 if pesos is None else float(pesos[i])
        d[int(v)] += w
        tot += w
    return ({k: (v / tot if tot else 0.0) for k, v in d.items()}, tot)


def w1_normalizado(p, q, k=5):
    """Wasserstein-1 discreto sobre escala ordinal, dividido por el diámetro."""
    acc = ap = aq = 0.0
    for i in range(1, k):
        ap += p[i]
        aq += q[i]
        acc += abs(ap - aq)
    return acc / (k - 1)


def media_sd(p):
    mu = sum(k * v for k, v in p.items())
    var = sum(v * (k - mu) ** 2 for k, v in p.items())
    return mu, math.sqrt(var)


def main():
    careo = json.loads(Path(sys.argv[1]).read_text())
    codigo = careo["codigo"]

    demo = cargar("ecp2023_democracia.zip")
    if codigo not in demo.columns:
        sys.exit(f"{codigo} no está en el módulo de democracia")

    # factor de expansión oficial: vive en la tabla de viviendas, se une por DIRECTORIO
    try:
        viv = cargar("ecp2023_viviendas.zip")
        col_fex = next((c for c in viv.columns if c.upper().startswith("FEX")), None)
    except Exception:
        viv, col_fex = None, None
    if col_fex:
        demo = demo.merge(viv[["DIRECTORIO", col_fex]].drop_duplicates("DIRECTORIO"),
                          on="DIRECTORIO", how="left")
        pesos = demo[col_fex].fillna(0).tolist()
        nota_peso = f"ponderado con {col_fex}"
    else:
        pesos, nota_peso = None, "SIN ponderar (no encontré el factor de expansión)"

    humanos = demo[codigo].tolist()
    p_hum, n_hum = distribucion(humanos, pesos)
    ns_hum = sum(1 for v in humanos if v == NS) / max(1, sum(1 for v in humanos if v == v))

    sint = [r["resp"] for r in careo["respuestas"]]
    p_sin, _ = distribucion(sint)
    validas = [v for v in sint if v is not None]
    ns_sin = sum(1 for v in validas if v == NS) / max(1, len(validas))

    mu_h, sd_h = media_sd(p_hum)
    mu_s, sd_s = media_sd(p_sin)
    w1 = w1_normalizado(p_sin, p_hum)

    print(f"\nCAREO — {codigo} · ECP 2023 del DANE ({nota_peso})")
    print(f"{careo['pregunta'][:150]}\n")
    print(f"{'opción':<34}{'humanos':>10}{'sintéticos':>13}{'  diferencia':>13}")
    print("-" * 71)
    ETIQ = {1: "1 muy insatisfecho", 2: "2 insatisfecho", 3: "3 ni una ni otra",
            4: "4 satisfecho", 5: "5 muy satisfecho"}
    for k in range(1, 6):
        d = 100 * (p_sin[k] - p_hum[k])
        print(f"{ETIQ.get(k, k):<34}{100*p_hum[k]:>9.1f}%{100*p_sin[k]:>12.1f}%{d:>+12.1f} pp")
    print("-" * 71)
    print(f"{'media de la escala':<34}{mu_h:>10.2f}{mu_s:>13.2f}{mu_s-mu_h:>+12.2f}")
    print(f"{'desviación estándar':<34}{sd_h:>10.2f}{sd_s:>13.2f}"
          f"{'  razón ' + format(sd_s/sd_h, '.2f') if sd_h else '':>13}")
    print(f"{'no sabe / no informa':<34}{100*ns_hum:>9.1f}%{100*ns_sin:>12.1f}%")
    print(f"\nW1 normalizado = {w1:.3f}   (0 = distribución idéntica · 1 = opuesta)")
    print(f"n humanos = {int(n_hum):,} expandidos · n sintéticos = {len(validas)}")
    veredicto = ("muy cerca" if w1 < 0.05 else "cerca" if w1 < 0.10
                 else "aceptable" if w1 < 0.20 else "lejos")
    print(f"Lectura: la distribución sintética está {veredicto.upper()} de la humana.")
    if sd_h and sd_s / sd_h < 0.8:
        print("⚠ SUB-DISPERSIÓN: las voces sintéticas opinan más parecido entre sí "
              "que los colombianos reales — el fallo clásico de este método.")


if __name__ == "__main__":
    main()
