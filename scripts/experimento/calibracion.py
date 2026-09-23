#!/usr/bin/env python3
"""¿El error del modelo sobre Colombia es sistemático? Si lo es, se corrige.

Para cada pregunta del banco con respuesta real conocida (ECP, LAPOP,
Latinobarómetro): la cifra real sale de los microdatos, y un modelo estima,
sin verla, qué % de colombianos diría que sí a una paráfrasis coloquial. Luego
se ajusta, en escala logit, verdad ~ a + b·estimación + c·valencia, donde la
valencia dice si "sí" es la respuesta que ve bien al país. La validación deja
fuera una encuesta entera: se entrena en dos y se mide en la tercera.

  uv run python scripts/experimento/calibracion.py verdad    <enjambre.json> <salida.json>
  uv run python scripts/experimento/calibracion.py estimar   <datos.json> <modelo>
  uv run python scripts/experimento/calibracion.py evaluar   <datos.json>
"""
import concurrent.futures as cf
import json
import math
import re
import sys
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts" / "experimento"))
sys.path.insert(0, str(RAIZ / "simcolombia" / "pipeline"))

# el mismo texto irá al proxy (acción estimar): si cambias uno, cambia el otro
INSTR_ESTIMAR = (
    "Eres un analista de opinión pública en Colombia. Te dan una pregunta de sí o no, "
    "como la escribiría cualquier persona. Estima qué porcentaje de los colombianos "
    "adultos respondería SÍ, entre quienes responden sí o no. Además, di si responder SÍ "
    "es ver con buenos ojos al país, sus instituciones, su gente o su situación "
    "(valencia 1), verlos con malos ojos (valencia -1), o ninguna de las dos (0). "
    "Responde SOLO JSON: {\"pct_si\": <0-100>, \"valencia\": <1|0|-1>}")


def _es_sino(op):
    return {v.lower().replace("í", "i").strip('"') for v in op.values()} <= {"si", "no"}


def verdad(enjambre, salida):
    """Cifra real ponderada: % de afirmativas entre sustantivas."""
    E = json.loads(Path(enjambre).read_text())
    par, et = E["parafrasis"], E["etiquetas"]
    banco = json.loads((RAIZ / "web" / "banco.json").read_text())
    import careo_ecp as C
    import fuentes_opinion as F
    demo = C.cargar("ecp2023_democracia.zip")
    viv = C.cargar("ecp2023_viviendas.zip")
    fex = next(c for c in viv.columns if c.upper().startswith("FEX"))
    demo = demo.merge(viv[["DIRECTORIO", fex]].drop_duplicates("DIRECTORIO"), on="DIRECTORIO", how="left")
    fuentes = {"LAPOP": F.lapop(), "LB": F.latinobarometro()}

    def pct(valores, pesos, afir, sust):
        a = s = 0.0
        for v, w in zip(valores, pesos):
            if v != v or w != w:
                continue
            k = str(int(v))
            if k in sust:
                s += w
                a += w if k in afir else 0
        return 100 * a / s if s else None

    out = []
    for b in banco:
        c = b["codigo"]
        if ":" in c:
            afir, sust = b.get("afirmativas"), b.get("sustantivas")
            if not afir or c not in par:
                continue
            base, num, _ = fuentes[c.split(":")[0]]
            v = pct(num[c.split(":", 1)[1]].to_numpy(), base["peso"].to_numpy(), set(afir), set(sust))
            q = par[c]
        else:
            if _es_sino(b["opciones"]):
                sino = {k for k, t in b["opciones"].items() if t.lower().replace("í", "i").strip('"') == "si"}
                afir, sust = sino, set(b["opciones"])
                q = par.get(c)
            elif c in et and et[c]["afirmativas"]:
                afir, sust, q = set(et[c]["afirmativas"]), set(et[c]["sustantivas"]), et[c]["pregunta_si"]
            else:
                continue
            if not q or c not in demo.columns:
                continue
            v = pct(demo[c].to_numpy(), demo[fex].fillna(0).to_numpy(), afir, sust)
        if v is not None:
            out.append({"codigo": c, "fuente": c.split(":")[0] if ":" in c else "ECP", "pregunta": q, "verdad": round(v, 2)})
    Path(salida).write_text(json.dumps(out, ensure_ascii=False, indent=0))
    print(f"{len(out)} preguntas con cifra real → {salida}")


def _llave():
    for l in (RAIZ / ".env").read_text().splitlines():
        if l.startswith("OPENROUTER_API_KEY="):
            return l.split("=", 1)[1].strip().strip("\"'")


def estimar_una(q, modelo, key):
    # razonamiento explícito solo donde está medido (docs/OPENROUTER.md); a los
    # demás no se les manda, y entonces tampoco se exige que lo soporten
    razona = {"effort": "low"} if "glm" in modelo else {"enabled": False} if "deepseek" in modelo else None
    body = {"model": modelo, "max_tokens": 60, "temperature": 0,
            **({"reasoning": razona} if razona else {}), "usage": {"include": True},
            "provider": {"require_parameters": bool(razona), "data_collection": "deny",
                         **({"order": ["deepinfra", "streamlake", "alibaba"]} if "deepseek" in modelo else {})},
            "messages": [{"role": "system", "content": INSTR_ESTIMAR}, {"role": "user", "content": q}]}
    for _ in range(3):
        try:
            req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=json.dumps(body).encode(),
                                         headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
            j = json.loads(urllib.request.urlopen(req, timeout=60).read())
            t = j["choices"][0]["message"]["content"]
            m = json.loads(re.search(r"\{.*\}", t, re.S).group(0))
            return float(m["pct_si"]), int(m["valencia"]), float(j.get("usage", {}).get("cost") or 0)
        except Exception:
            continue
    return None, None, 0.0


def estimar(datos, modelo):
    D = json.loads(Path(datos).read_text())
    key = _llave()
    with cf.ThreadPoolExecutor(12) as ex:
        res = list(ex.map(lambda d: estimar_una(d["pregunta"], modelo, key), D))
    corto = modelo.split("/")[-1]
    for d, (p, v, _) in zip(D, res):
        d.setdefault("est", {})[corto] = {"pct": p, "val": v}
    Path(datos).write_text(json.dumps(D, ensure_ascii=False, indent=0))
    ok = sum(p is not None for p, _, _ in res)
    print(f"{corto}: {ok}/{len(D)} estimaciones · ${sum(c for _, _, c in res):.4f}")


def _lg(p):
    p = min(max(p / 100, 0.01), 0.99)
    return math.log(p / (1 - p))


def _inv(x):
    return 100 / (1 + math.exp(-x))


def _ajuste(filas):
    """mínimos cuadrados de logit(verdad) ~ 1 + logit(est) + valencia"""
    X = [[1.0, _lg(p), float(v)] for p, v, _ in filas]
    y = [_lg(t) for _, _, t in filas]
    n = 3
    A = [[sum(X[k][i] * X[k][j] for k in range(len(X))) for j in range(n)] for i in range(n)]
    b = [sum(X[k][i] * y[k] for k in range(len(X))) for i in range(n)]
    for i in range(n):                          # Gauss con un poco de ridge
        A[i][i] += 1e-6
    for i in range(n):
        piv = A[i][i]
        for j in range(i, n):
            A[i][j] /= piv
        b[i] /= piv
        for r in range(n):
            if r != i:
                f = A[r][i]
                for j in range(i, n):
                    A[r][j] -= f * A[i][j]
                b[r] -= f * b[i]
    return b


def _pred(coef, p, v):
    return _inv(coef[0] + coef[1] * _lg(p) + coef[2] * v)


def evaluar(datos):
    D = json.loads(Path(datos).read_text())
    modelos = sorted({m for d in D for m in d.get("est", {})})
    for m in modelos:
        F = [(d["est"][m]["pct"], d["est"][m]["val"], d["verdad"], d["fuente"]) for d in D
             if d.get("est", {}).get(m, {}).get("pct") is not None]
        crudo = sum(abs(p - t) for p, _, t, _ in F) / len(F)
        # ¿sistemático? error con signo según valencia
        for val in (1, -1, 0):
            sub = [p - t for p, v, t, _ in F if v == val]
            if sub:
                print(f"  {m} valencia {val:+d}: n={len(sub)} sesgo medio {sum(sub) / len(sub):+.1f} pts")
        print(f"{m}: n={len(F)} · error crudo {crudo:.1f} pts")
        for fuera in ("ECP", "LAPOP", "LB"):
            tr = [(p, v, t) for p, v, t, f in F if f != fuera]
            te = [(p, v, t) for p, v, t, f in F if f == fuera]
            if len(tr) < 10 or not te:
                continue
            c = _ajuste(tr)
            e0 = sum(abs(p - t) for p, _, t in te) / len(te)
            e1 = sum(abs(_pred(c, p, v) - t) for p, v, t in te) / len(te)
            peor = max(abs(_pred(c, p, v) - t) - abs(p - t) for p, v, t in te)
            print(f"   fuera {fuera:<6} n={len(te):>3}: crudo {e0:5.1f} → calibrado {e1:5.1f}  "
                  f"(peor ítem {peor:+.1f}; coef {c[0]:+.2f} {c[1]:+.2f} {c[2]:+.2f})")


if __name__ == "__main__":
    {"verdad": lambda: verdad(sys.argv[2], sys.argv[3]),
     "estimar": lambda: estimar(sys.argv[2], sys.argv[3]),
     "evaluar": lambda: evaluar(sys.argv[2])}[sys.argv[1]]()
