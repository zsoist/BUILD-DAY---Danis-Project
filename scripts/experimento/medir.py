#!/usr/bin/env python3
"""Medidor determinista del experimento A/B "¿son personas reales?".
Ninguna métrica la juzga un LLM: todo se calcula en Python sobre el texto crudo.
A = andamiaje de producción · B = control desnudo (mismos residentes, misma pregunta)."""
import json
import re
import sys
import unicodedata
from collections import Counter
from math import sqrt
from statistics import mean, pstdev

RUTA = sys.argv[1]
D = json.loads(open(RUTA).read())


def limpia(t):
    """Quita la etiqueta de postura y normaliza espacios."""
    return re.sub(r"\[POSTURA[^\]]*\]?", "", t or "", flags=re.I).strip()


def palabras(t):
    t = unicodedata.normalize("NFKD", limpia(t).lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.findall(r"[a-zñ']+", t)


FUNCION = {"que", "de", "la", "el", "los", "las", "un", "una", "y", "o", "a", "en",
           "por", "para", "con", "sin", "no", "se", "lo", "es", "si", "mas", "ni",
           "su", "al", "del", "me", "te", "le", "yo", "uno", "eso", "esa", "ese"}


def ngramas(ws, n=4):
    """N-gramas propios de la voz: se descartan los que solo repiten el vocabulario
    de la pregunta o palabras función — si no, se mide el tema, no el meme."""
    out = set()
    for i in range(len(ws) - n + 1):
        g = ws[i:i + n]
        if all(w in VOCAB_PREGUNTA or w in FUNCION for w in g):
            continue
        out.add(" ".join(g))
    return out


def postura(t):
    m = re.search(r"\[POSTURA:?\s*(a_favor|en_contra|depende|ni_ni)", t or "", re.I)
    return m.group(1).lower() if m else None


# ── métricas ────────────────────────────────────────────────────────────────

VOCAB_PREGUNTA = set(palabras(D["pregunta"]))


def indice_manada(lote):
    """% de pares de voces DISTINTAS que comparten al menos un 4-grama.
    Gente real en una encuesta casi nunca coincide en 4 palabras seguidas."""
    gs = [ngramas(palabras(r["texto"])) for r in lote]
    js = []
    for i in range(len(gs)):
        for j in range(i + 1, len(gs)):
            u = len(gs[i] | gs[j])
            if u:
                js.append(len(gs[i] & gs[j]) / u)
    return 100.0 * mean(js) if js else 0.0


def ngramas_compartidos(lote, top=6):
    """Los 4-gramas que más voces distintas repiten (la huella del meme)."""
    c = Counter()
    for r in lote:
        for g in ngramas(palabras(r["texto"])):
            c[g] += 1
    return [(g, n) for g, n in c.most_common(top * 3) if n > 1][:top]


def diversidad_lexica(lote):
    """Type-token ratio agregado: vocabulario distinto / palabras totales."""
    tot, vocab = 0, set()
    for r in lote:
        ws = palabras(r["texto"])
        tot += len(ws)
        vocab |= set(ws)
    return 100.0 * len(vocab) / tot if tot else 0.0


def arranques_distintos(lote):
    """% de primeras-3-palabras únicas: si todos abren igual, es plantilla."""
    ini = [" ".join(palabras(r["texto"])[:3]) for r in lote if palabras(r["texto"])]
    return 100.0 * len(set(ini)) / len(ini) if ini else 0.0


def variacion_largo(lote):
    """Coeficiente de variación del largo. Gente real varía mucho (CV>0.45);
    un bot tiende a la uniformidad métrica."""
    ls = [len(palabras(r["texto"])) for r in lote if r["texto"]]
    return pstdev(ls) / mean(ls) if ls and mean(ls) else 0.0


def correlacion(xs, ys):
    """Pearson sin dependencias."""
    n = len(xs)
    if n < 3:
        return 0.0
    mx, my = mean(xs), mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
    return num / den if den else 0.0


NIVEL = {"ninguna": 0, "primaria": 1, "secundaria": 2, "media": 3, "superior": 4}


def senal_educacion(lote):
    """¿La educación de la ficha se NOTA al hablar? Correlación entre nivel
    educativo y largo medio de palabra (proxy de registro culto).
    En población real es positiva; si da ~0, el andamiaje no se oye."""
    xs, ys = [], []
    for r in lote:
        n = NIVEL.get((r.get("educacion") or "").lower())
        ws = palabras(r["texto"])
        if n is None or len(ws) < 8:
            continue
        xs.append(n)
        ys.append(mean(len(w) for w in ws))
    return correlacion(xs, ys), len(xs)


def obediencia_libreto(lote):
    """% que terminó del lado que su ficha le asignó (excluye ni_ni/indiferentes)."""
    ok = tot = 0
    for r in lote:
        p, gl = postura(r["texto"]), r.get("libreto") or ""
        if not p or p in ("ni_ni",) or r.get("compromiso") == "indiferente":
            continue
        tot += 1
        if (("A FAVOR" in gl and p == "a_favor") or ("EN CONTRA" in gl and p == "en_contra")
                or ("dividido" in gl and p == "depende")):
            ok += 1
    return (100.0 * ok / tot if tot else 0.0), tot


def marco_vs_postura(lote):
    """¿El marco social conservador predice la postura? Diferencia en puntos
    porcentuales de 'en_contra' entre conservadores y liberales."""
    g = {"cons": [], "lib": []}
    for r in lote:
        p = postura(r["texto"])
        if not p or p == "ni_ni":
            continue
        k = "cons" if "conservador" in (r.get("marco") or "") else "lib"
        g[k].append(1 if p == "en_contra" else 0)
    if len(g["cons"]) < 3 or len(g["lib"]) < 3:
        return None, len(g["cons"]), len(g["lib"])
    return 100 * (mean(g["cons"]) - mean(g["lib"])), len(g["cons"]), len(g["lib"])


def cramers_v(lote, campo):
    """V de Cramér entre un atributo de la ficha y la postura: cuánta OPINIÓN queda
    determinada por la IDENTIDAD. La literatura (arXiv:2607.26348) reporta que los
    LLM sobredeterminan: ~1.5% de varianza en humanos vs hasta 67% en modelos.
    Valores altos = caricatura demográfica, no diversidad real."""
    filas, cols = {}, {}
    tabla = {}
    n = 0
    for r in lote:
        p = postura(r["texto"])
        k = r.get(campo)
        if not p or not k:
            continue
        k = "conservador" if "conservador" in str(k) else str(k)
        tabla[(k, p)] = tabla.get((k, p), 0) + 1
        filas[k] = filas.get(k, 0) + 1
        cols[p] = cols.get(p, 0) + 1
        n += 1
    if n < 8 or len(filas) < 2 or len(cols) < 2:
        return None
    chi2 = 0.0
    for f, nf in filas.items():
        for c, nc in cols.items():
            esp = nf * nc / n
            obs = tabla.get((f, c), 0)
            chi2 += (obs - esp) ** 2 / esp if esp else 0
    k = min(len(filas), len(cols)) - 1
    return sqrt(chi2 / (n * k)) if k else None


def etiqueta_ok(lote):
    return 100.0 * sum(1 for r in lote if postura(r["texto"])) / len(lote)


def distribucion(lote):
    c = Counter(postura(r["texto"]) or "sin_postura" for r in lote)
    return dict(c)


TICS = ["no me quita el sueno", "puro show", "pa la foto", "prometen y no cumplen",
        "no entendi", "al final del dia", "es como cuando uno", "ni me va ni me viene",
        "la plata no alcanza", "todos son iguales"]


def tics(lote):
    """Cuántas voces usan alguna frase de manada conocida."""
    n = 0
    for r in lote:
        t = " ".join(palabras(r["texto"]))
        if any(x in t for x in TICS):
            n += 1
    return 100.0 * n / len(lote)


def reporte(nombre, lote):
    ed, ned = senal_educacion(lote)
    ob, nob = obediencia_libreto(lote)
    mv, nc, nl = marco_vs_postura(lote)
    return {
        "lote": nombre,
        "n": len(lote),
        "manada_jaccard_%": round(indice_manada(lote), 2),
        "diversidad_lexica_%": round(diversidad_lexica(lote), 1),
        "arranques_distintos_%": round(arranques_distintos(lote), 1),
        "variacion_largo_CV": round(variacion_largo(lote), 3),
        "largo_medio_palabras": round(mean([len(palabras(r["texto"])) for r in lote]), 1),
        "senal_educacion_r": round(ed, 3),
        "senal_educacion_n": ned,
        "obediencia_libreto_%": round(ob, 1),
        "obediencia_n": nob,
        "marco_predice_pp": None if mv is None else round(mv, 1),
        "marco_n": f"{nc}c/{nl}l",
        "caricatura_V_marco": (lambda v: None if v is None else round(v, 3))(cramers_v(lote, "marco")),
        "caricatura_V_lean": (lambda v: None if v is None else round(v, 3))(cramers_v(lote, "lean")),
        "etiqueta_presente_%": round(etiqueta_ok(lote), 1),
        "tics_manada_%": round(tics(lote), 1),
        "distribucion": distribucion(lote),
    }


A, B = reporte("A · andamiaje", D["A"]), reporte("B · control", D["B"])

print(f"\nEXPERIMENTO «¿son personas reales?» — n={D['n']} residentes, mismos en ambos lotes")
print(f"Pregunta: {D['pregunta']}\n")
CLAVES = [("manada_jaccard_%", "Índice de manada (4-gramas propios compartidos)", "menor"),
          ("diversidad_lexica_%", "Diversidad léxica (vocabulario/palabras)", "mayor"),
          ("arranques_distintos_%", "Arranques distintos", "mayor"),
          ("variacion_largo_CV", "Variación de largo (CV)", "mayor"),
          ("largo_medio_palabras", "Largo medio (palabras)", "—"),
          ("senal_educacion_r", "Señal de educación (r edad→registro)", "mayor"),
          ("obediencia_libreto_%", "Obediencia al libreto asignado", "mayor"),
          ("marco_predice_pp", "Marco social predice postura (pp)", "mayor"),
          ("caricatura_V_marco", "Caricatura: identidad→opinión (V Cramér)", "menor"),
          ("etiqueta_presente_%", "Etiqueta de postura presente", "mayor"),
          ("tics_manada_%", "Voces con tic de manada", "menor")]
print(f"{'MÉTRICA':<46}{'A andamiaje':>13}{'B control':>12}   mejor")
print("-" * 86)
for k, etiqueta, dir_ in CLAVES:
    a, b = A[k], B[k]
    if a is None or b is None:
        mejor = "n/a"
    elif dir_ == "—":
        mejor = "—"
    else:
        gana_a = (a > b) if dir_ == "mayor" else (a < b)
        mejor = "A ✓" if gana_a else ("B" if a != b else "=")
    fa = f"{a}" if a is not None else "n/a"
    fb = f"{b}" if b is not None else "n/a"
    print(f"{etiqueta:<46}{fa:>13}{fb:>12}   {mejor}")
print("-" * 86)
print(f"{'distribución de postura':<46}{str(A['distribucion'])}")
print(f"{'':<46}{str(B['distribucion'])}")
print("\n4-gramas repetidos entre voces (huella de meme):")
for lote, nom in ((D["A"], "A"), (D["B"], "B")):
    gs = ngramas_compartidos(lote)
    print(f"  {nom}: " + (", ".join(f"«{g}»×{n}" for g, n in gs) if gs else "ninguno ✓"))
json.dump({"A": A, "B": B}, open(RUTA.replace(".json", "_metricas.json"), "w"),
          ensure_ascii=False, indent=1)
print(f"\n→ {RUTA.replace('.json', '_metricas.json')}")
