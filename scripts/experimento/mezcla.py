#!/usr/bin/env python3
"""¿Contar posturas con la etiqueta de la voz, o mezclarla con SSR?

Cada voz del sitio devuelve texto + etiqueta [POSTURA: …]. Hoy el sitio cuenta
la etiqueta. La mezcla reparte a cada voz como
    α · etiqueta  +  (1-α) · distribución SSR de su texto
sobre (sí, no, depende, no sé). α=1 es el sitio hoy; α=0 es SSR solo.

Regla fijada ANTES de ver datos (y endurecida tras una auditoría adversarial):
  α* = el de menor error medio en calibración (P5261S1-S8).
  Se despliega la mezcla solo si, en la prueba ciega:
    1. error medio ≥ 2 pts menor que la etiqueta sola
    2. el IC 95% bootstrap de la mejora no toca 0
    3. ningún ítem ciego empeora > 10 pts
    4. el ítem de calibración con menos "sí" (P5261S4, 4%) no empeora > 10 pts
    5. la proporción de decididos no cae > 15 pts
    6. la conclusión se sostiene sin P5317S7 (sus etiquetas se vieron antes)

  uv run python scripts/experimento/mezcla.py <carpeta con cal_*.json y ciega_*.json>
"""
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import postura as P   # noqa: E402  verdad del DANE + anclas genéricas
import ssr as S       # noqa: E402

ALFAS = [0.0, 0.25, 0.5, 0.75, 1.0]
IDX = {"a_favor": 0, "en_contra": 1, "depende": 2, "ni_ni": 3}
VISTO = "P5317S7"
BAJO = "P5261S4"


def voces(ruta):
    """Por voz: (índice de etiqueta o None, pmf SSR de 4)."""
    D = json.loads(Path(ruta).read_text())
    rs = [r for r in D["respuestas"] if len((r.get("crudo") or "").strip()) >= 8]
    vecs = S.embeber(P.GENERICAS + [r["crudo"].strip() for r in rs])
    va, vr = vecs[:4], vecs[4:]
    out = []
    for r, v in zip(rs, vr):
        pmf = S.pmf_de([S.coseno(v, a) for a in va], P.TEMP)
        out.append((IDX.get(r.get("resp")), pmf))
    return D["codigo"], out


def medir(vs, alfa):
    """% sí entre decididos y proporción de decididos, con la mezcla α."""
    acc = [0.0] * 4
    for tag, pmf in vs:
        a = alfa if tag is not None else 0.0      # sin etiqueta: solo SSR
        for k in range(4):
            acc[k] += a * (1.0 if k == tag else 0.0) + (1 - a) * pmf[k]
    dec = acc[0] + acc[1]
    return (acc[0] / dec if dec else float("nan")), dec / len(vs)


def error(vs, alfa, humano):
    si, dec = medir(vs, alfa)
    return abs(si - humano) * 100, dec


def boot(items, alfa, n=2000, semilla=7):
    """IC 95% de la mejora media (etiqueta − mezcla) re-muestreando voces."""
    rnd = random.Random(semilla)
    difs = []
    for _ in range(n):
        d = []
        for vs, h in items:
            m = [vs[rnd.randrange(len(vs))] for _ in vs]
            d.append(error(m, 1.0, h)[0] - error(m, alfa, h)[0])
        difs.append(sum(d) / len(d))
    difs.sort()
    return difs[int(0.025 * n)], difs[int(0.975 * n)]


def correlacion(vs):
    """¿La etiqueta y el SSR dicen lo mismo? Pearson entre 1[sí] y p(sí) − p(no)."""
    xs = [(1.0 if t == 0 else -1.0 if t == 1 else 0.0) for t, _ in vs if t is not None]
    ys = [p[0] - p[1] for t, p in vs if t is not None]
    n = len(xs)
    if n < 3:
        return float("nan")
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    sx = sum((a - mx) ** 2 for a in xs) ** 0.5
    sy = sum((b - my) ** 2 for b in ys) ** 0.5
    return sxy / (sx * sy) if sx and sy else float("nan")


def tabla(nombre, datos, alfas):
    print(f"\n{nombre}")
    cab = f"{'ítem':<10}{'humano':>8}" + "".join(f"{'α='+str(a):>9}" for a in alfas) + f"{'r':>7}"
    print(cab)
    print("-" * len(cab))
    for cod, vs, h in datos:
        fila = f"{cod:<10}{100*h:>7.1f}%"
        for a in alfas:
            fila += f"{error(vs, a, h)[0]:>9.1f}"
        print(fila + f"{correlacion(vs):>7.2f}")
    medias = {a: sum(error(vs, a, h)[0] for _, vs, h in datos) / len(datos) for a in alfas}
    print(f"{'media':<18}" + "".join(f"{medias[a]:>9.1f}" for a in alfas))
    return medias


def main():
    carpeta = Path(sys.argv[1])
    cal, ciega = [], []
    for f in sorted(carpeta.glob("cal_*.json")):
        cod, vs = voces(f)
        cal.append((cod, vs, P.humano(cod)[0]))
    for f in sorted(carpeta.glob("ciega_*.json")):
        cod, vs = voces(f)
        ciega.append((cod, vs, P.humano(cod)[0]))

    print("error en puntos del % de 'sí' entre decididos · r = correlación etiqueta–SSR")
    m_cal = tabla("CALIBRACIÓN (P5261)", cal, ALFAS)
    alfa = min(ALFAS, key=lambda a: m_cal[a])
    print(f"\nα* elegido en calibración: {alfa}")
    if alfa == 1.0:
        print("La etiqueta sola gana en calibración: no hay mezcla que probar.")

    m_cie = tabla("PRUEBA CIEGA", ciega, sorted({alfa, 1.0}))

    peor = max(error(vs, alfa, h)[0] - error(vs, 1.0, h)[0] for _, vs, h in ciega)
    bajo = next(((vs, h) for c, vs, h in cal if c == BAJO), None)
    dano_bajo = error(bajo[0], alfa, bajo[1])[0] - error(bajo[0], 1.0, bajo[1])[0] if bajo else 0
    dec_tag = sum(medir(vs, 1.0)[1] for _, vs, _ in ciega) / len(ciega)
    dec_mix = sum(medir(vs, alfa)[1] for _, vs, _ in ciega) / len(ciega)
    lo, hi = boot([(vs, h) for _, vs, h in ciega], alfa) if alfa < 1 else (0, 0)
    sin7 = [(vs, h) for c, vs, h in ciega if c != VISTO]
    mej7 = (sum(error(vs, 1.0, h)[0] - error(vs, alfa, h)[0] for vs, h in sin7) / len(sin7))
    mejora = m_cie[1.0] - m_cie[alfa]

    reglas = [
        ("mejora media ≥ 2 pts", mejora >= 2, f"{mejora:+.1f}"),
        ("IC 95% de la mejora sin 0", lo > 0, f"[{lo:+.1f}, {hi:+.1f}]"),
        ("ningún ítem ciego empeora > 10", peor <= 10, f"peor {peor:+.1f}"),
        (f"{BAJO} (4% sí) no empeora > 10", dano_bajo <= 10, f"{dano_bajo:+.1f}"),
        ("decididos no caen > 15 pts", dec_mix >= dec_tag - 0.15, f"{100*dec_tag:.0f}% → {100*dec_mix:.0f}%"),
        (f"se sostiene sin {VISTO}", mej7 >= 2, f"{mej7:+.1f}"),
    ]
    print(f"\nREGLA DE DESPLIEGUE (α={alfa})")
    for nombre, ok, val in reglas:
        print(f"  {'✓' if ok else '✗'} {nombre:<34} {val}")
    todo = alfa < 1 and all(ok for _, ok, _ in reglas)
    print(f"\nVEREDICTO: {'SE DESPLIEGA la mezcla' if todo else 'NO se despliega'}")


if __name__ == "__main__":
    main()
