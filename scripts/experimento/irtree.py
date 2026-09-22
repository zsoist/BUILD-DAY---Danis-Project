#!/usr/bin/env python3
"""Discretizador psicométrico: saca la escala de encuesta FUERA del modelo.

El problema medido: cuando al modelo se le dan cinco opciones etiquetadas, sus
respuestas las gobiernan sesgos de formato (orden, etiqueta, atracción al punto
medio) y no la opinión. Resultado: dispersión colapsada y extremos vacíos.

La solución viene de la psicometría, no de la IA. El modelo entrega una
INTENSIDAD CONTINUA (0-100) y aquí, en Python, un árbol de respuesta al ítem
(IRTree) con umbrales PROPIOS DE CADA PERSONA la convierte en 1-5 o en "no sé":

    nodo 0  ¿tiene opinión formada?   -> si no, "no sé"
    nodo 1  ¿se queda en el medio?    -> si sí, 3
    nodo 2  ¿hacia qué lado?          -> positivo / negativo
    nodo 3  ¿con qué intensidad?      -> extremo (1 o 5) / moderado (2 o 4)

Cada residente lleva tres parámetros deterministas por hash de su id:
    e_p  estilo extremo    (>0 usa los extremos, <0 se refugia en el medio)
    s_p  aquiescencia      (<0 le cuesta menos decir que algo está bien)
    g_p  propensión a opinar (bajo -> dice "no sé")

Los parámetros POBLACIONALES se calibran una sola vez contra las marginales de
la ECP y se validan en preguntas que no se usaron para calibrar. Calibrar por
pregunta sería enseñarle al examen.
"""
import hashlib
import json
import math
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
CAL = Path(__file__).resolve().parent / "irtree_calibracion.json"

# Umbrales poblacionales de arranque (escala latente centrada en 0).
BASE = {"b": [-1.4, -0.45, 0.45, 1.4], "e_mu": 0.35, "e_sd": 0.45,
        "s_mu": 0.0, "s_sd": 0.40, "g_mu": 3.13, "g_sd": 1.0}


def _u(semilla, sal):
    """Uniforme(0,1) determinista a partir del id del residente."""
    h = hashlib.sha256(f"{semilla}|{sal}".encode()).digest()
    return int.from_bytes(h[:6], "big") / float(1 << 48)


def _normal(semilla, sal, mu, sd):
    """Normal determinista (Box-Muller sobre dos uniformes del mismo id)."""
    u1 = max(_u(semilla, sal + "a"), 1e-9)
    u2 = _u(semilla, sal + "b")
    return mu + sd * math.sqrt(-2 * math.log(u1)) * math.cos(2 * math.pi * u2)


def estilo_de(rid, par=None):
    """Los tres parámetros de estilo de respuesta de un residente."""
    p = par or BASE
    return {
        "e": _normal(rid, "ers", p["e_mu"], p["e_sd"]),
        "s": _normal(rid, "ars", p["s_mu"], p["s_sd"]),
        "g": _normal(rid, "opi", p["g_mu"], p["g_sd"]),
    }


def _sigmoide(x):
    return 1.0 / (1.0 + math.exp(-max(-40.0, min(40.0, x))))


def discretizar(rid, intensidad, par=None):
    """intensidad 0-100 del modelo -> categoría 1..5 o 99 ('no sé').

    Los umbrales se comprimen o se abren según el estilo extremo de la persona:
    un e alto acerca los umbrales al centro, así que cruza antes a los extremos.
    """
    p = par or BASE
    est = estilo_de(rid, p)

    # nodo 0: ¿tiene opinión formada? (determinista, sin azar extra)
    if _sigmoide(est["g"]) < _u(rid, "ns"):
        return 99

    # 0-100 -> latente aproximadamente N(0,1)
    theta = (float(intensidad) - 50.0) / 18.0

    # umbrales propios: escalados por el estilo extremo, desplazados por aquiescencia
    k = math.exp(-est["e"])
    taus = [b * k + est["s"] for b in p["b"]]

    cat = 1
    for t in taus:
        if theta > t:
            cat += 1
    return cat


def marginales(pares, par=None):
    """[(id, intensidad)] -> proporciones 1..5 (excluyendo 'no sé') y tasa de NS."""
    c = {k: 0 for k in range(1, 6)}
    ns = 0
    for rid, inten in pares:
        v = discretizar(rid, inten, par)
        if v == 99:
            ns += 1
        else:
            c[v] += 1
    tot = sum(c.values())
    return ({k: (v / tot if tot else 0.0) for k, v in c.items()},
            ns / max(1, len(pares)))


def w1(p, q, k=5):
    acc = ap = aq = 0.0
    for i in range(1, k):
        ap += p[i]
        aq += q[i]
        acc += abs(ap - aq)
    return acc / (k - 1)


def calibrar(pares, objetivo, ns_objetivo, pasos=1200):
    """Ajusta los parámetros POBLACIONALES para acercarse a las marginales reales.

    Búsqueda de coordenadas simple: sin dependencias, determinista y auditable.
    Se calibra UNA vez y se valida en preguntas distintas.
    """
    par = dict(BASE)
    par["b"] = list(BASE["b"])

    def coste(p):
        m, ns = marginales(pares, p)
        return w1(m, objetivo) + abs(ns - ns_objetivo)

    mejor = coste(par)
    claves = ["e_mu", "e_sd", "s_mu", "g_mu"]
    paso = {"e_mu": 0.20, "e_sd": 0.15, "s_mu": 0.20, "g_mu": 0.50}
    for _ in range(pasos // len(claves)):
        mejora = False
        for k in claves:
            for signo in (1, -1):
                cand = dict(par)
                cand[k] = par[k] + signo * paso[k]
                if k == "e_sd" and cand[k] <= 0.05:
                    continue
                c = coste(cand)
                if c < mejor - 1e-6:
                    par, mejor, mejora = cand, c, True
        if not mejora:
            for k in claves:
                paso[k] *= 0.5
            if max(paso.values()) < 0.01:
                break
    return par, mejor


if __name__ == "__main__":
    import sys
    print("Parámetros de arranque:", json.dumps(BASE, ensure_ascii=False))
    if CAL.exists():
        print("Calibración guardada:", CAL.read_text()[:300])
    else:
        print("Sin calibración todavía — córrela con careo_irtree.py")
