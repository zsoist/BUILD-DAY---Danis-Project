#!/usr/bin/env python3
"""¿El simulador reproduce las DIFERENCIAS ENTRE GRUPOS que tienen los humanos?

Para cada ítem con corridas de voces y cifra real (ECP, LAPOP, Latinobarómetro),
y cada dimensión (edad, sexo, educación, región ECP), compara la brecha real
entre grupos (ej. % sí <30 − % sí 60+) con la simulada. Todo en Python.

Brechas (contrastes):
  edad   <30 − 60+          sexo  hombre − mujer
  edu    superior − primaria o menos
  región cada región ECP − el resto del país (5 contrastes)

Métricas por modo:
  · dirección: % de contrastes con el mismo signo (solo brechas reales ≥5 pts y
    ambos grupos con ≥15 voces decididas)
  · error de brecha: |simulada − real| en pts, frente a decir "no hay brecha"
    (error = |real|) y frente a un simulador perfecto con el mismo n (ruido de
    muestreo binomial: E|N(0,se)| y P(signo correcto) = Φ(|brecha|/se))
  · r: correlación entre desvíos de grupo (grupo − nacional) reales y simulados

La verdad sale de los microdatos locales; aquí solo se imprimen agregados.

  ETIQUETAS=enjambre.json SALIDA=filas.json \\
  uv run python scripts/experimento/grupos.py <modo>=<glob>[,<glob>...] ...
"""
import glob
import json
import math
import os
import sys
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts" / "experimento"))
sys.path.insert(0, str(RAIZ / "simcolombia" / "pipeline"))
from donantes_ecp import REGION, grupo_edad, grupo_edu_ecp, grupo_edu_res  # noqa: E402

LLAVES = ["DIRECTORIO", "NRO_ENCUESTA", "HOGAR_NUMERO", "PERSONA_NUMERO"]
MIN_N = 15          # voces decididas por grupo para contar el contraste
MIN_BRECHA = 5.0    # pts: brecha real mínima para exigir dirección
CONTRASTES = [("edad", 0, 3, "edad <30 − 60+"), ("sexo", 1, 2, "sexo H − M"),
              ("edu", 2, 0, "edu sup − prim")] + \
             [("region", r, None, f"región {n} − resto") for r, n in
              ((1, "Bogotá"), (2, "Caribe"), (3, "Oriental"), (4, "Central"), (5, "Pacífica"))]


def _es_sino(op):
    return {v.lower().replace("í", "i").strip('"') for v in op.values()} <= {"si", "no"}


def cargar_verdad(codigos):
    """{codigo: DataFrame con columnas si (1/0), peso, edad(ge), sexo, edu, region}"""
    import careo_ecp as C
    import fuentes_opinion as F
    import pandas as pd
    banco = {b["codigo"]: b for b in json.loads((RAIZ / "web" / "banco.json").read_text())}
    # etiquetas afirmativa/sustantiva de ítems ECP que no son sí/no (del enjambre)
    et = json.loads(Path(os.environ["ETIQUETAS"]).read_text())["etiquetas"] if os.environ.get("ETIQUETAS") else {}
    out = {}
    ecp = [c for c in codigos if ":" not in c]
    if ecp:
        demo = C.cargar("ecp2023_democracia.zip")
        car = C.cargar("ecp2023_caracteristicas.zip")
        viv = C.cargar("ecp2023_viviendas.zip")
        df = demo.merge(car[LLAVES + ["P220", "P5785", "P6210"]], on=LLAVES, how="inner")
        df = df.merge(viv[["DIRECTORIO", "REGION", "FEX_P"]].drop_duplicates("DIRECTORIO"), on="DIRECTORIO", how="left")
        df = df[(df["P5785"] >= 18) & df["P6210"].between(1, 7) & df["REGION"].notna()]
        dem = pd.DataFrame({"edad": df["P5785"].map(grupo_edad), "sexo": df["P220"].astype(int),
                            "edu": df["P6210"].astype(int).map(grupo_edu_ecp),
                            "region": df["REGION"].astype(int), "peso": df["FEX_P"].fillna(0)})
        for c in ecp:
            b = banco.get(c)
            if b and _es_sino(b["opciones"]):
                afir = {k for k, t in b["opciones"].items() if t.lower().replace("í", "i").strip('"') == "si"}
                sust = set(b["opciones"])
            elif c in et and et[c]["afirmativas"]:
                afir, sust = set(et[c]["afirmativas"]), set(et[c]["sustantivas"])
            else:
                print(f"  ! {c}: sin afirmativas, fuera")
                continue
            VERDAD_ETIQ[c] = (afir, sust)
            v = df[c].map(lambda x: None if x != x else str(int(x)))
            ok = v.isin(sust)
            d = dem[ok].copy()
            d["si"] = v[ok].isin(afir).astype(float)
            out[c] = d
    for pref, carga in (("LAPOP", F.lapop), ("LB", F.latinobarometro)):
        cods = [c for c in codigos if c.startswith(pref + ":")]
        if not cods:
            continue
        base, num, _ = carga()
        base = base.dropna(subset=["region", "sexo", "edad", "edu"])
        for c in cods:
            b = banco.get(c)
            if not b or not b.get("afirmativas"):
                print(f"  ! {c}: no está en web/banco.json con afirmativas, fuera")
                continue
            afir, sust = set(b["afirmativas"]), set(b["sustantivas"])
            v = num.loc[base.index, c.split(":", 1)[1]].map(lambda x: None if x != x else str(int(x)))
            ok = v.isin(sust)
            d = pd.DataFrame({"edad": base.loc[ok, "edad"].map(grupo_edad), "sexo": base.loc[ok, "sexo"].astype(int),
                              "edu": base.loc[ok, "edu"].astype(int), "region": base.loc[ok, "region"].astype(int),
                              "peso": base.loc[ok, "peso"].fillna(0), "si": v[ok].isin(afir).astype(float)})
            out[c] = d
    return out


def real_pct(d, dim, val, resto=False):
    m = (d[dim] != val) if resto else (d[dim] == val)
    w = d.loc[m, "peso"]
    return (100 * (d.loc[m, "si"] * w).sum() / w.sum(), int(m.sum())) if w.sum() > 0 else (None, 0)


def voces(archivos):
    """{codigo: [(grupos, si 0/1 o None), ...]} con todas las corridas del modo, y
    {codigo: {id: grupos}} para contar voces únicas"""
    resp, unicas = defaultdict(list), defaultdict(dict)
    for f in archivos:
        j = json.loads(Path(f).read_text())
        for r in j["respuestas"]:
            g = {"edad": grupo_edad(r["edad"]), "sexo": 1 if r["sexo"] == "hombre" else 2,
                 "edu": grupo_edu_res(r["educacion"]), "region": REGION.get(r["dpto"])}
            si = {"a_favor": 1, "en_contra": 0}.get(r["resp"])
            resp[j["codigo"]].append((g, si))
            if si is not None:
                unicas[j["codigo"]][r["id"]] = g
    return resp, unicas


def sim_pct(lst, dim, val, resto=False):
    xs = [si for g, si in lst if si is not None and ((g[dim] != val) if resto else (g[dim] == val))]
    return (100 * sum(xs) / len(xs), len(xs)) if xs else (None, 0)


def n_unicas(u, dim, val, resto=False):
    return sum(1 for g in u.values() if ((g[dim] != val) if resto else (g[dim] == val)))


def phi(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def medir(modo, archivos, verdad):
    resp, unicas = voces(archivos)
    filas = []
    for c, lst in resp.items():
        if c not in verdad:
            continue
        d, u = verdad[c], unicas[c]
        runs = max(1, sum(1 for f in archivos if json.loads(Path(f).read_text())["codigo"] == c))
        for dim, a, b, et in CONTRASTES:
            resto = b is None
            ra, _ = real_pct(d, dim, a)
            rb, _ = real_pct(d, dim, a if resto else b, resto)
            sa, _ = sim_pct(lst, dim, a)
            sb, _ = sim_pct(lst, dim, a if resto else b, resto)
            na, nb = n_unicas(u, dim, a), n_unicas(u, dim, a if resto else b, resto)
            if ra is None or rb is None:
                continue
            real = ra - rb
            sim = None if sa is None or sb is None else sa - sb
            # ruido de un simulador perfecto con las mismas voces únicas
            se = math.sqrt(max(ra * (100 - ra), 1) / max(na, 1) + max(rb * (100 - rb), 1) / max(nb, 1))
            filas.append({"modo": modo, "codigo": c, "dim": dim, "contraste": et, "real": real, "sim": sim,
                          "na": na, "nb": nb, "ok_n": na >= MIN_N and nb >= MIN_N, "se": se, "runs": runs})
    return filas


def desvios(modo, archivos, verdad):
    """pares (real, sim) de desvío grupo − nacional, grupos con ≥MIN_N voces"""
    resp, unicas = voces(archivos)
    pares = []
    for c, lst in resp.items():
        if c not in verdad:
            continue
        d = verdad[c]
        rn = 100 * (d["si"] * d["peso"]).sum() / d["peso"].sum()
        xs = [si for _, si in lst if si is not None]
        if not xs:
            continue
        sn = 100 * sum(xs) / len(xs)
        for dim, vals in (("edad", range(4)), ("sexo", (1, 2)), ("edu", range(3)), ("region", range(1, 6))):
            for v in vals:
                if n_unicas(unicas[c], dim, v) < MIN_N:
                    continue
                r, _ = real_pct(d, dim, v)
                s, _ = sim_pct(lst, dim, v)
                if r is not None and s is not None:
                    pares.append((r - rn, s - sn, dim))
    return pares


def corr(p):
    if len(p) < 3:
        return float("nan")
    xs, ys = [a for a, *_ in p], [b for _, b, *_ in p]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy) if sx and sy else float("nan")


def resumen(filas, etiqueta):
    ok = [f for f in filas if f["ok_n"] and f["sim"] is not None]
    dirf = [f for f in ok if abs(f["real"]) >= MIN_BRECHA]
    acierto = sum(1 for f in dirf if f["sim"] * f["real"] > 0)
    err = [abs(f["sim"] - f["real"]) for f in ok]
    nulo = [abs(f["real"]) for f in ok]
    perf_err = [f["se"] * math.sqrt(2 / math.pi) for f in ok]
    perf_dir = [phi(abs(f["real"]) / f["se"]) for f in dirf]
    items = len({f["codigo"] for f in filas})
    m = lambda xs: sum(xs) / len(xs) if xs else float("nan")  # noqa: E731
    return {"etiqueta": etiqueta, "items": items, "contrastes": len(filas), "con_n": len(ok),
            "dir_n": len(dirf), "dir_ok": acierto, "dir_pct": 100 * acierto / len(dirf) if dirf else float("nan"),
            "dir_perfecto": 100 * m(perf_dir), "err": m(err), "err_nulo": m(nulo), "err_perfecto": m(perf_err),
            "sim_abs": m([abs(f["sim"]) for f in ok])}


def _imul(a, b):
    return (a * b) & 0xFFFFFFFF


def voto_celda(r, D, codigo):
    """copia de votoCelda() de web/index.html: la respuesta que el ancla de
    LAPOP/LB le asigna a una voz (tablas de una variable combinadas + hash)"""
    e = r["edad"]
    perfil = {"region": REGION.get(r["dpto"]), "sexo": 1 if r["sexo"] == "hombre" else 2,
              "ge": grupo_edad(e), "edu": grupo_edu_res(r["educacion"])}
    nac = D["*"]
    orden = sorted([k for k in nac if k.isdigit()], key=int) + [k for k in nac if not k.isdigit()]  # orden de JS
    p, tot = {}, 0.0
    for v in orden:
        x = nac[v]
        for dim, val in perfil.items():
            t = D.get(dim, {}).get(str(val))
            if t and nac[v] > 0:
                x *= t.get(v, 0) / nac[v]
        p[v] = x
        tot += x
    ps = [(v, p[v]) for v in orden] if tot > 0 else [(v, nac[v]) for v in orden]
    T = tot if tot > 0 else 1
    h = 2166136261
    for ch in r["id"] + "|" + codigo:
        h ^= ord(ch)
        h = _imul(h, 16777619)
    h ^= h >> 16
    h = _imul(h, 0x85ebca6b)
    h ^= h >> 13
    h = _imul(h, 0xc2b2ae35)
    h ^= h >> 16
    x = h / 4294967296 * T
    for v, q in ps:
        x -= q
        if x < 0:
            return None if v == "ns" else v
    return None if ps[-1][0] == "ns" else ps[-1][0]


def ancla_sola(codigos, verdad, muestra=None):
    """Brecha que lleva el ANCLA sola (si cada voz obedeciera al 100%), sobre
    todos los adultos sintéticos o sobre una muestra de ids. Sin LLM."""
    res = json.loads((RAIZ / "web" / "residents_v2.json").read_text())
    res = [r for r in (res if isinstance(res, list) else res["residentes"]) if r["edad"] >= 18]
    if muestra:
        res = [r for r in res if r["id"] in muestra]
    banco = {b["codigo"]: b for b in json.loads((RAIZ / "web" / "banco.json").read_text())}
    E = json.loads((RAIZ / "web" / "respuestas_ecp.json").read_text())
    filas = []
    for c in codigos:
        if c not in verdad:
            continue
        b = banco.get(c, {})
        if ":" in c:
            f = RAIZ / "web" / "opinion" / (c.replace(":", "_") + ".json")
            if not f.exists() or not b.get("afirmativas"):
                continue
            D = json.loads(f.read_text())
            afir, sust = set(b["afirmativas"]), set(b["sustantivas"])
            votos = {r["id"]: voto_celda(r, D, c) for r in res}
        else:
            if c not in E["items"]:
                continue
            k = E["items"].index(c)
            d = verdad[c]
            afir, sust = VERDAD_ETIQ[c]
            votos = {r["id"]: (None if (E["por_id"].get(r["id"]) or [None] * (k + 1))[k] is None
                               else str(E["por_id"][r["id"]][k])) for r in res}
        lst = []
        for r in res:
            v = votos[r["id"]]
            g = {"edad": grupo_edad(r["edad"]), "sexo": 1 if r["sexo"] == "hombre" else 2,
                 "edu": grupo_edu_res(r["educacion"]), "region": REGION.get(r["dpto"])}
            lst.append((g, None if v not in sust else int(v in afir)))
        d = verdad[c]
        for dim, a, bb, et in CONTRASTES:
            resto = bb is None
            ra, _ = real_pct(d, dim, a)
            rb, _ = real_pct(d, dim, a if resto else bb, resto)
            sa, na = sim_pct(lst, dim, a)
            sb, nb = sim_pct(lst, dim, a if resto else bb, resto)
            if None in (ra, rb, sa, sb):
                continue
            se = math.sqrt(max(ra * (100 - ra), 1) / max(na, 1) + max(rb * (100 - rb), 1) / max(nb, 1))
            filas.append({"codigo": c, "dim": dim, "contraste": et, "real": ra - rb, "sim": sa - sb,
                          "na": na, "nb": nb, "ok_n": na >= MIN_N and nb >= MIN_N, "se": se})
    return filas


VERDAD_ETIQ = {}


def main():
    if sys.argv[1:2] == ["--ancla"]:
        banco = json.loads((RAIZ / "web" / "banco.json").read_text())
        cods = [b["codigo"] for b in banco if (":" in b["codigo"] and b.get("afirmativas")) or
                (":" not in b["codigo"] and _es_sino(b["opciones"]))]
        verdad = cargar_verdad(cods)
        filas = ancla_sola(list(verdad), verdad)
        s = resumen(filas, "ancla sola")
        r = corr([(f["real"], f["sim"]) for f in filas])
        print(f"ANCLA SOLA, todos los adultos sintéticos ({s['items']} ítems, {s['contrastes']} contrastes):"
              f" dirección {s['dir_ok']}/{s['dir_n']} ({s['dir_pct']:.0f}%) · err {s['err']:.1f} · nulo {s['err_nulo']:.1f}"
              f" · |sim| {s['sim_abs']:.1f} · r brechas {r:.2f}")
        for fuente, pred in (("ECP", lambda c: ":" not in c), ("LAPOP/LB", lambda c: ":" in c)):
            ff = [f for f in filas if pred(f["codigo"])]
            s = resumen(ff, fuente)
            for dim in ("edad", "sexo", "edu", "region"):
                sd = resumen([f for f in ff if f["dim"] == dim], fuente)
                print(f"  {fuente:<9}{dim:<7} dirección {sd['dir_ok']:>3}/{sd['dir_n']:<3} ({sd['dir_pct']:3.0f}%)"
                      f" · err {sd['err']:4.1f} · nulo {sd['err_nulo']:4.1f} · |real| {sd['err_nulo']:4.1f} |sim| {sd['sim_abs']:4.1f}"
                      f" · r {corr([(f['real'], f['sim']) for f in ff if f['dim'] == dim]):.2f}")
        # techo por tamaño de muestra: un simulador PERFECTO (humanos de verdad) con n voces por grupo
        reales = [abs(f["real"]) for f in filas if f["dim"] != "region" or True]
        grandes = [x for x in reales if x >= MIN_BRECHA]
        print(f"\nSimulador perfecto con n voces decididas POR GRUPO (brechas reales de {len(reales)} contrastes;"
              f" {100 * len(grandes) / len(reales):.0f}% ≥5 pts, {100 * sum(x >= 10 for x in reales) / len(reales):.0f}% ≥10):")
        for n in (4, 5, 10, 20, 50, 100, 200, 400):
            se = math.sqrt(2 * 2500 / n)
            dir_ = sum(phi(x / se) for x in grandes) / len(grandes)
            sig = sum(1 - phi(1.96 - x / se) for x in reales) / len(reales)
            print(f"  n={n:<4} acierta dirección {100 * dir_:3.0f}% · error esperado {se * math.sqrt(2 / math.pi):4.1f} pts"
                  f" · brecha 'significativa' (95%) en {100 * sig:3.0f}% de los contrastes")
        return
    modos = []
    for a in sys.argv[1:]:
        nombre, globs = a.split("=", 1)
        arch = sorted({f for g in globs.split(",") for f in glob.glob(g)})
        modos.append((nombre, arch))
    codigos = sorted({json.loads(Path(f).read_text())["codigo"] for _, arch in modos for f in arch})
    verdad = cargar_verdad(codigos)
    todo = {}
    print(f"\n{'modo':<22}{'ítems':>6}{'contr.':>7}{'n≥15':>6}{'dirección':>14}{'perfecto':>9}"
          f"{'err':>7}{'nulo':>7}{'perf.':>7}{'|sim|':>7}{'r desv':>8}")
    for nombre, arch in modos:
        filas = medir(nombre, arch, verdad)
        todo[nombre] = filas
        s = resumen(filas, nombre)
        r = corr(desvios(nombre, arch, verdad))
        print(f"{nombre:<22}{s['items']:>6}{s['contrastes']:>7}{s['con_n']:>6}"
              f"{s['dir_ok']:>6}/{s['dir_n']:<3}{s['dir_pct']:>4.0f}%{s['dir_perfecto']:>8.0f}%"
              f"{s['err']:>7.1f}{s['err_nulo']:>7.1f}{s['err_perfecto']:>7.1f}{s['sim_abs']:>7.1f}{r:>8.2f}")
    print("\ndirección = mismo signo, brechas reales ≥5 pts con ambos grupos ≥15 voces · perfecto = lo que acertaría"
          "\nun simulador perfecto con esas n · err = |brecha sim − real| (pts) · nulo = decir 'no hay brecha' ·"
          "\nperf. = error esperado solo por muestreo · |sim| = tamaño medio de la brecha simulada · r desv = corr."
          "\nde desvíos grupo−nacional (real vs sim)")
    print("\npor dimensión (dirección aciertos/total · err · nulo):")
    for nombre, filas in todo.items():
        partes = []
        for dim in ("edad", "sexo", "edu", "region"):
            s = resumen([f for f in filas if f["dim"] == dim], nombre)
            partes.append(f"{dim} {s['dir_ok']}/{s['dir_n']} · {s['err']:.1f} · {s['err_nulo']:.1f}")
        print(f"  {nombre:<20} " + "   ".join(partes))
    # brechas reales: ¿qué tan grandes son?
    reales = {}
    for filas in todo.values():
        for f in filas:
            reales[(f["codigo"], f["contraste"])] = (f["real"], f["dim"])
    print(f"\nbrechas reales ({len({k[0] for k in reales})} ítems): |brecha| media por dimensión y % ≥10 pts")
    for dim in ("edad", "sexo", "edu", "region"):
        xs = [abs(v) for v, d in reales.values() if d == dim]
        if xs:
            print(f"  {dim:<7} media {sum(xs) / len(xs):5.1f} · ≥10 pts {100 * sum(x >= 10 for x in xs) / len(xs):4.0f}%"
                  f" · máx {max(xs):5.1f}  (n={len(xs)})")
    if os.environ.get("SALIDA"):
        Path(os.environ["SALIDA"]).write_text(json.dumps(todo))
    return todo


if __name__ == "__main__":
    main()
