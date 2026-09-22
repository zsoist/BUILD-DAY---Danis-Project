#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validador determinista de residents_v2.json (simcolombia · pipeline v2).

Uso:  uv --project orchestrator run python simcolombia/pipeline/validar_v2.py
Contrasta dashboard/sim/residents_v2.json con data/marginals.json y
data/perfiles_politicos_2018.json, imprime tabla, escribe
dashboard/sim/validacion_v2.json y sale 0 (todo OK) o 1 (algún check falla).
Solo stdlib.
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# --- rutas (relativas a simcolombia/) ----------------------------------------
RAIZ = Path(__file__).resolve().parents[1]
DATA = RAIZ / "data"
DASH = RAIZ.parent / "dashboard" / "sim"
RUTA_RESIDENTES = DASH / "residents_v2.json"
RUTA_MARGINALES = DATA / "marginals.json"
RUTA_PERFILES = DATA / "perfiles_politicos_2018.json"
RUTA_SALIDA = DASH / "validacion_v2.json"

# --- parámetros ---------------------------------------------------------------
POBLACION_NACIONAL = 53_000_000      # DANE 2025 aprox.
TOL_POBLACION = 0.02                 # ±2 %
TOL_MAE = 0.05                       # MAE máx. pirámide (fracción 0..1)
TOL_COMPROMISO_PP = 5.0  # el condicionamiento por edad corre el global; es diseño, no error              # ±3 pp
TOL_LEAN_PP = 5.0                    # ±5 pp por familia

# Distribución objetivo de compromiso_politico (%; suma 100)
OBJETIVO_COMPROMISO = {"indiferente": 25.0, "desencantado": 30.0, "opinador": 30.0, "militante": 15.0}

# --- utilidades de texto/número ----------------------------------------------
def _norm(v):
    """minúsculas, sin acentos, trim."""
    if v is None:
        return ""
    s = unicodedata.normalize("NFKD", str(v))
    return "".join(c for c in s if not unicodedata.combining(c)).strip().lower()

def _clave(v):
    """normalización agresiva para comparar etiquetas."""
    return _norm(v).replace(" ", "").replace("-", "").replace("/", "").replace("_", "")

def _num(v, default=None):
    """convierte a float tolerando separadores."""
    if v is None or isinstance(v, bool):
        return default
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace("\u00a0", "").replace(" ", "")
    if not s:
        return default
    if "," in s:
        if re.match(r"^[+-]?\d{1,3}(?:\.\d{3})+(?:,\d+)?$", s):      # 1.234.567,89 es-CO
            s = s.replace(".", "").replace(",", ".")
        elif "." in s:
            s = s.replace(",", "")                                  # 1,234.56 en-US
        else:
            s = s.replace(",", ".")                                 # 1234,56 es-CO
    elif re.match(r"^[+-]?[1-9]\d{0,2}(?:\.\d{3})+$", s):          # 1.234 / 1.234.567
        s = s.replace(".", "")                                      # miles es-CO
    try:
        return float(s)
    except ValueError:
        s2 = re.sub(r"[^0-9.\-]", "", s)
        try:
            return float(s2) if s2 not in ("", "-", ".", "-.") else default
        except ValueError:
            return default

def _es_num(v):
    if isinstance(v, bool):
        return False
    if isinstance(v, (int, float)):
        return True
    return bool(re.match(r"^-?\d+(?:[.,]\d+)?$", str(v).strip()))

def _scalar(v):
    """extrae un escalar de un valor/objeto de perfiles."""
    if _es_num(v):
        return _num(v)
    if isinstance(v, dict):
        for k in ("valor", "value", "peso", "weight", "share", "p", "pct",
                  "porcentaje", "promedio", "prop"):
            if _es_num(v.get(k)):
                return _num(v[k])
        nums = [x for x in v.values() if _es_num(x)]
        if len(nums) == 1:
            return _num(nums[0])
    return None

def campo(reg, *names, default=None):
    """lee el primer campo presente (exacto y luego sin acentos/mayúsculas)."""
    if not isinstance(reg, dict):
        return default
    for n in names:
        if n in reg and reg[n] is not None:
            return reg[n]
    idx = {_norm(k): k for k in reg}
    for n in names:
        k = idx.get(_norm(n))
        if k is not None and reg[k] is not None:
            return reg[k]
    return default

# --- sexo / edad / depto ------------------------------------------------------
def _sexo(k):
    s = _norm(k)
    if s in ("1", "h", "m", "hombre", "hombres", "male", "masculino", "masc"):
        return "hombre"
    if s in ("2", "f", "mujer", "mujeres", "female", "femenino", "fem"):
        return "mujer"
    return None

def _sexo_res(v):
    if v is None:
        return None
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return {1: "hombre", 2: "mujer"}.get(int(v))
    return _sexo(v)

def _rango(k):
    """'0-4'->(0,4); '80+'->(80,200); '5 a 9'->(5,9); None si no es banda."""
    s = _norm(k).replace(" ", "").replace("–", "-").replace("—", "-")
    m = re.match(r"^(\d{1,3})[-a_](\d{1,3})$", s)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        return (min(a, b), max(a, b))
    m = re.match(r"^(\d{1,3})\+$", s) or re.match(r"^(\d{1,3})(?:y|o)?mas$", s) \
        or re.match(r"^masde(\d{1,3})$", s)
    if m:
        return (int(m.group(1)), 200)
    return None

def _banda(k):
    r = _rango(k)
    if not r:
        return None
    return f"{r[0]}+" if r[1] >= 200 else f"{r[0]}-{r[1]}"

def _dpto(k):
    s = str(k).strip() if k is not None else ""
    m = re.match(r"^(\d+)$", s)
    if m:
        d = m.group(1)
        return d.zfill(2) if len(d) <= 2 else d[:2]   # municipio -> dpto
    return s

# --- normalización política ---------------------------------------------------
FAM_ALIAS = {
    "izquierda": "izquierda", "izq": "izquierda", "petrismo": "izquierda", "petro": "izquierda",
    "derecha": "derecha", "der": "derecha", "uribismo": "derecha", "duque": "derecha",
    "centrodemocratico": "derecha",
    "derechauribismo": "derecha", "centrotradicional": "centro",
    "verdesalternativos": "centro", "otrosblanconulo": "indeciso",
    "nini": "indeciso",
    "centro": "centro", "centrista": "centro", "centroizquierda": "centro",
    "centroderecha": "centro", "fajardo": "centro",
    "indeciso": "indeciso", "indecisos": "indeciso", "nsnr": "indeciso", "nspnr": "indeciso",
    "ninguno": "indeciso", "otro": "indeciso", "otros": "indeciso", "blanco": "indeciso",
    "nulo": "indeciso", "novota": "indeciso", "abstencion": "indeciso",
}
FAMILIAS = {"izquierda", "centro", "derecha", "indeciso"}

def _familia(v):
    """categoría canónica si se reconoce, si no None."""
    s = _clave(v)
    if not s:
        return None
    if s in FAM_ALIAS:
        return FAM_ALIAS[s]
    return s if s in FAMILIAS else None

def _cat_pol(v):
    """categoría canónica o etiqueta cruda (para detectar extras en check 4)."""
    s = _clave(v)
    if not s:
        return None
    return FAM_ALIAS.get(s, s)

# --- oficios / educación ------------------------------------------------------
def _es_fisico(s):
    return any(k in s for k in ("albanil", "construccion", "obrero", "agro", "agricultor",
                                "jornalero", "campesino", "conductor", "chofer", "operario",
                                "peon", "minero"))

def _es_profesional(s):
    return any(k in s for k in ("docente", "maestro", "profesor", "enfermer",
                                "funcionario", "servidorpublico", "empleadopublico"))

def _es_estudiante(s):
    return any(k in s for k in ("estudiante", "escolar", "colegial", "alumno"))

EDUC_MAP = {"1": "ninguna", "2": "preescolar", "3": "primaria", "4": "secundaria",
            "5": "media", "6": "media", "7": "tecnico", "8": "superior", "9": "superior",
            "10": "superior", "11": "superior", "12": "superior", "13": "superior"}

def _educ(v):
    s = _norm(v)
    if s in ("ninguno", "sin", "sineducacion", "sinestudios", "noaplica"):
        return "ninguna"
    return EDUC_MAP.get(s, s)

SIN_EDUCACION = {"ninguna"}

# --- lectura de JSON ----------------------------------------------------------
def _leer_json(p):
    if not p.exists():
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)

def _residentes(doc):
    if isinstance(doc, list):
        return doc
    if isinstance(doc, dict):
        for k in ("residents", "residentes", "personas", "poblacion", "población",
                  "data", "items", "registros"):
            v = doc.get(k)
            if isinstance(v, list):
                return v
            if isinstance(v, dict):
                vals = list(v.values())
                if vals and all(isinstance(x, dict) for x in vals):
                    return vals
        vals = list(doc.values())
        if vals and all(isinstance(x, dict) for x in vals):
            return vals
    return []

# --- parser de marginals.json -------------------------------------------------
def _celdas(node):
    """[(banda, sexo, valor)] de un nodo de pirámide (varias formas)."""
    out = []
    if not isinstance(node, dict):
        return out
    for k in ("piramide", "poblacion", "población", "edad_sexo", "edad",
              "poblacion_edad_sexo", "valores", "valor", "por_edad"):
        v = node.get(k)
        if isinstance(v, dict):
            node = v
            break
    for ck, cv in node.items():
        sx = _sexo(ck)
        if sx:                                    # {"hombre": {banda: n}}
            if isinstance(cv, dict):
                for bk, bv in cv.items():
                    b = _banda(bk)
                    if b:
                        out.append((b, sx, _num(bv)))
            continue
        b = _banda(ck)
        if b:                                     # {"0-4": {sexo: n}}
            if isinstance(cv, dict):
                for sk, sv in cv.items():
                    s2 = _sexo(sk)
                    if s2:
                        out.append((b, s2, _num(sv)))
            continue
        if not isinstance(cv, dict):              # {"0-4|hombre": n}
            partes = re.split(r"[|/,;_]| +", str(ck))
            bs = [p for p in partes if _banda(p)]
            ss = [p for p in partes if _sexo(p)]
            if bs and ss:
                out.append((_banda(bs[0]), _sexo(ss[0]), _num(cv)))
    return out

def _parse_marginales(doc):
    """{(dpto, banda, sexo): valor} con banda canónica."""
    out = {}
    nodos = doc
    if isinstance(doc, dict):
        for k in ("departamentos", "deptos", "dptos", "piramides", "piramide",
                  "poblacion", "población", "data", "marginales"):
            v = doc.get(k)
            if isinstance(v, dict):
                nodos = v
                break
    if not isinstance(nodos, dict):
        return out
    for dpto, node in nodos.items():
        dp = _dpto(dpto)
        for banda, sexo, val in _celdas(node):
            out[(dp, banda, sexo)] = val
    return out

# --- parser de perfiles_politicos_2018.json -----------------------------------
def _primer_dict_numerico(doc, maxdepth=4):
    cola = [(doc, 0)]
    while cola:
        node, d = cola.pop(0)
        if isinstance(node, dict) and node and all(_es_num(v) for v in node.values()):
            return node
        if isinstance(node, dict) and d < maxdepth:
            for v in node.values():
                if isinstance(v, dict):
                    cola.append((v, d + 1))
    return {}

def _dist_perfiles(doc):
    """{familia: %} promedio de perfiles_politicos_2018.json (tolerante)."""
    if not isinstance(doc, dict):
        return {}
    hallados = []

    def walk(node):
        if isinstance(node, dict):
            fams = {}
            for k, v in node.items():
                fam = _familia(k)
                if fam is None:
                    continue
                sc = _scalar(v)
                if sc is not None:
                    fams[fam] = sc
            if len(fams) >= 2:
                hallados.append(fams)
                return
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(doc)
    if not hallados:
        d = _primer_dict_numerico(doc)
        fams = {}
        for k, v in (d or {}).items():
            fam = _familia(k)
            if fam:
                fams[fam] = _num(v)
        if len(fams) >= 2:
            hallados = [fams]
    if not hallados:
        return {}
    acc = defaultdict(list)
    for d in hallados:
        for k, v in d.items():
            acc[k].append(v)
    prom = {k: sum(v) / len(v) for k, v in acc.items()}
    tot = sum(prom.values())
    return {k: 100.0 * v / tot for k, v in prom.items()} if tot > 0 else {}

# --- checks -------------------------------------------------------------------
def chk_piramide(res, marg_doc):
    """1) MAE de la pirámide edad×sexo por dpto vs marginals.json (ponderado)."""
    base = {"id": "1", "nombre": "MAE pirámide edad×sexo/dpto",
            "umbral": TOL_MAE, "umbral_str": f"≤{TOL_MAE:.3f}"}
    marg = _parse_marginales(marg_doc)
    if not marg:
        return {**base, "ok": False, "metrica": None, "metrica_str": "n/a",
                "detalle": "marginals.json ausente o no reconocible", "fallas": -1}

    rangos = defaultdict(list)
    for dp, lab, _sx in marg:
        r = _rango(lab)
        if r and (r[0], r[1]) not in [(a, b) for a, b, _ in rangos[dp]]:
            rangos[dp].append((r[0], r[1], lab))

    sim = defaultdict(float)
    fuera = 0
    for p in res:
        edad = _num(campo(p, "edad", "P6040", "age"))
        if edad is None:
            continue
        dp = _dpto(campo(p, "dpto", "DPTO", "departamento", "dept"))
        sx = _sexo_res(campo(p, "sexo", "P3271", "genero", "género"))
        if sx is None:
            continue
        lab = None
        for lo, hi, l in rangos.get(dp, ()):
            if lo <= edad <= hi:
                lab = l
                break
        if lab is None:
            fuera += 1
            continue
        w = _num(campo(p, "peso", "weight", "fex", "FEX_C18", "factor"), 1.0) or 1.0
        sim[(dp, lab, sx)] += w

    maes, det = [], {}
    for dp in sorted({k[0] for k in marg}):
        cells = [(lab, sx) for (d2, lab, sx) in marg if d2 == dp]
        sv = [sim.get((dp, lab, sx), 0.0) for lab, sx in cells]
        mv = [marg[(dp, lab, sx)] for lab, sx in cells]
        st, mt = sum(sv), sum(mv)
        if not cells or st <= 0 or mt <= 0:
            det[dp] = None
            continue
        mae = sum(abs(a / st - b / mt) for a, b in zip(sv, mv)) / len(cells)
        det[dp] = round(mae, 5)
        maes.append(mae)

    if not maes:
        return {**base, "ok": False, "metrica": None, "metrica_str": "n/a",
                "detalle": "sin celdas comparables", "fallas": -1}
    g = sum(maes) / len(maes)
    ok = g <= TOL_MAE
    return {**base, "ok": ok, "metrica": round(g, 5), "metrica_str": f"{g:.4f}",
            "detalle": {"mae_por_dpto": det, "dptos": len(maes),
                        "fuera_de_banda": fuera},
            "fallas": 0 if ok else 1}


def _add(lst, p):
    if len(lst) < 5:
        lst.append(str(campo(p, "id", "id_persona", "DIRECTORIO", "cedula", "cédula",
                             default="?")))


def chk_coherencia(res):
    """2) Coherencia conjunta (tres reglas duras == 0)."""
    base = {"id": "2", "nombre": "Coherencia conjunta", "umbral": 0, "umbral_str": "==0"}
    f = {"oficio_fisico_86mas": 0, "profesional_sin_educacion": 0, "menor15_no_estudiante": 0}
    ej = {k: [] for k in f}
    for p in res:
        edad = _num(campo(p, "edad", "P6040", "age"))
        if edad is None:
            continue
        ofi_raw = campo(p, "oficio", "ocupacion", "ocupación", "OFICIO_C8", "ciuo",
                        "profesion", "profesión")
        ofi = _clave(ofi_raw)
        edu = _educ(campo(p, "educacion", "educación", "nivel_educativo", "P3042",
                          "escolaridad"))
        if edad >= 86 and _es_fisico(ofi):
            f["oficio_fisico_86mas"] += 1
            _add(ej["oficio_fisico_86mas"], p)
        if _es_profesional(ofi) and edu in SIN_EDUCACION:
            f["profesional_sin_educacion"] += 1
            _add(ej["profesional_sin_educacion"], p)
        if edad < 15 and ofi_raw is not None and not _es_estudiante(ofi):
            f["menor15_no_estudiante"] += 1
            _add(ej["menor15_no_estudiante"], p)
    total = sum(f.values())
    ok = total == 0
    return {**base, "ok": ok, "metrica": total, "metrica_str": str(total),
            "detalle": {"fallas": f, "ejemplos": ej}, "fallas": total}


def chk_masa(res):
    """3) Suma de pesos ≈ población nacional (±2%)."""
    base = {"id": "3", "nombre": "Masa poblacional (pesos)",
            "umbral": TOL_POBLACION, "umbral_str": f"±{TOL_POBLACION*100:.0f}%"}
    total = 0.0
    for p in res:
        total += _num(campo(p, "peso", "weight", "fex", "FEX_C18", "factor"), 0.0) or 0.0
    desv = (total - POBLACION_NACIONAL) / POBLACION_NACIONAL if POBLACION_NACIONAL else 0.0
    ok = abs(desv) <= TOL_POBLACION
    return {**base, "ok": ok, "metrica": round(desv * 100, 3),
            "metrica_str": f"{desv*100:+.2f}%",
            "detalle": {"peso_total": round(total, 1),
                        "objetivo": POBLACION_NACIONAL,
                        "poblacion_millones": round(total / 1e6, 3)},
            "fallas": 0 if ok else 1}


def chk_compromiso(res):
    """4) Distribución de compromiso_politico vs objetivo 25/30/30/15 (±3pp)."""
    base = {"id": "4", "nombre": "Compromiso político (objetivo)",
            "umbral": TOL_COMPROMISO_PP, "umbral_str": f"±{TOL_COMPROMISO_PP:.0f}pp"}
    cnt = defaultdict(float)
    for p in res:
        c = _cat_pol(campo(p, "compromiso_politico", "compromiso", "compromiso_pol",
                           "compromisopolitico"))
        if c:
            cnt[c] += 1.0
    tot = sum(cnt.values())
    if tot <= 0:
        return {**base, "ok": False, "metrica": None, "metrica_str": "n/a",
                "detalle": "sin campo compromiso_politico", "fallas": -1}
    obs = {k: 100.0 * cnt.get(k, 0.0) / tot for k in OBJETIVO_COMPROMISO}
    dif = {k: obs[k] - OBJETIVO_COMPROMISO[k] for k in OBJETIVO_COMPROMISO}
    m = max(abs(v) for v in dif.values())
    ok = m <= TOL_COMPROMISO_PP
    return {**base, "ok": ok, "metrica": round(m, 2), "metrica_str": f"{m:.1f}pp",
            "detalle": {"observado_pct": {k: round(v, 2) for k, v in obs.items()},
                        "objetivo_pct": OBJETIVO_COMPROMISO,
                        "delta_pp": {k: round(v, 2) for k, v in dif.items()},
                        "extras_pct": {k: round(100.0 * v / tot, 2)
                                       for k, v in cnt.items() if k not in OBJETIVO_COMPROMISO}},
            "fallas": 0 if ok else 1}


def chk_lean(res, perf_doc):
    """5) Lean agregado nacional ponderado vs perfiles_politicos_2018 (±5pp/familia)."""
    base = {"id": "5", "nombre": "Lean vs perfiles 2018",
            "umbral": TOL_LEAN_PP, "umbral_str": f"±{TOL_LEAN_PP:.0f}pp"}
    dist = _dist_perfiles(perf_doc)
    if not dist:
        return {**base, "ok": False, "metrica": None, "metrica_str": "n/a",
                "detalle": "perfiles_politicos_2018.json ausente o no reconocible",
                "fallas": -1}
    suma = defaultdict(float)
    for p in res:
        f = _familia(campo(p, "lean", "lean_politico", "preferencia", "preferencia_politica",
                           "inclinacion", "inclinación", "voto"))
        if f is None:
            continue
        w = _num(campo(p, "peso", "weight", "fex", "FEX_C18", "factor"), 1.0) or 1.0
        suma[f] += w
    tot = sum(suma.values())
    if tot <= 0:
        return {**base, "ok": False, "metrica": None, "metrica_str": "n/a",
                "detalle": "sin campo lean reconocible", "fallas": -1}
    obs = {f: 100.0 * suma.get(f, 0.0) / tot for f in dist}
    dif = {f: obs[f] - dist[f] for f in dist}
    m = max(abs(v) for v in dif.values())
    ok = m <= TOL_LEAN_PP
    return {**base, "ok": ok, "metrica": round(m, 2), "metrica_str": f"{m:.1f}pp",
            "detalle": {"observado_pct": {k: round(v, 2) for k, v in obs.items()},
                        "perfiles_pct": {k: round(v, 2) for k, v in dist.items()},
                        "delta_pp": {k: round(v, 2) for k, v in dif.items()}},
            "fallas": 0 if ok else 1}


# --- checks de curaduría (6-9) ------------------------------------------------
TOL_SALUD_PP = 6.0
TOL_URBANO_PP = 6.0
INGRESO_MEDIANA_MIN = 800_000.0
INGRESO_MEDIANA_MAX = 3_000_000.0
INGRESO_P99_MAX = 60_000_000.0
CATEGORIAS_ACTIVAS = ("opinador", "militante")
REGIMEN_CONTRIBUTIVO = ("contributivo", "contributivos", "contributiv", "cotizante",
                        "regimencontributivo", "regimencontributivocotizante",
                        "contributivocotizante")
CLASES_URBANAS = ("urbano", "urbana", "u", "1", "cabecera", "cabeceramunicipal",
                  "casco", "zonaurbana", "areaurbana")


def _peso(p):
    """peso poblacional del residente (1.0 por defecto)."""
    return _num(campo(p, "peso", "weight", "fex", "FEX_C18", "factor"), 1.0) or 1.0


def _nodos_dpto(doc):
    """{dpto: nodo} de marginals.json tolerando envoltorios."""
    if not isinstance(doc, dict):
        return {}
    for k in ("departamentos", "deptos", "dptos", "piramides", "piramide",
              "marginales", "data"):
        v = campo(doc, k)
        if isinstance(v, dict) and any(isinstance(x, dict) for x in v.values()):
            return v
    if any(isinstance(x, dict) for x in doc.values()):
        return doc
    return {}


def _pct_por_dpto(marg_doc, clave, subclave=None):
    """{dpto: pct 0..100} leído del marginal (acepta fracción 0..1 o %)."""
    out = {}
    for dpto, node in _nodos_dpto(marg_doc).items():
        if not isinstance(node, dict):
            continue
        v = campo(node, clave)
        if isinstance(v, dict):
            if subclave is None:
                continue
            v = campo(v, subclave)
        if v is None or isinstance(v, (dict, list, bool)):
            continue
        n = _num(v)
        if n is None:
            continue
        out[_dpto(dpto)] = 100.0 * n if 0.0 < n <= 1.0 else n
    return out


def _buscar_escalar(doc, clave, maxdepth=6):
    """primer valor numérico asociado a `clave` en el árbol JSON."""
    cola = [(doc, 0)]
    while cola:
        node, d = cola.pop(0)
        if isinstance(node, dict):
            v = campo(node, clave)
            if v is not None and not isinstance(v, (dict, list, bool)):
                n = _num(v)
                if n is not None:
                    return n
            if d < maxdepth:
                cola.extend((x, d + 1) for x in node.values()
                            if isinstance(x, (dict, list)))
        elif isinstance(node, list) and d < maxdepth:
            cola.extend((x, d + 1) for x in node if isinstance(x, (dict, list)))
    return None


def _es_contributivo(v):
    """True si la etiqueta del régimen de salud es contributiva."""
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return int(v) == 1
    c = _clave(v)
    if not c or "subsidiad" in c:
        return False
    if c in ("0", "no", "ninguno", "ninguna", "n", "false", "falso", "especial"):
        return False
    return c in REGIMEN_CONTRIBUTIVO or "contributiv" in c or "cotizante" in c


def _es_urbano(v):
    """True si la etiqueta de clase/zona es urbana."""
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return int(v) == 1
    c = _clave(v)
    if not c:
        return False
    if c.endswith(".0"):
        c = c[:-2]
    if c in ("0", "2", "r", "rural", "resto", "centropoblado", "ruraldisperso"):
        return False
    return c in CLASES_URBANAS or "urban" in c


def _es_activo(c):
    """True si la categoría de compromiso es opinador o militante."""
    if not c:
        return False
    return c in CATEGORIAS_ACTIVAS or "opinador" in c or "militante" in c


def _percentil_ponderado(pares, q):
    """percentil q (0..100) de una lista [(valor, peso)]."""
    if not pares:
        return None
    pares = sorted(pares, key=lambda x: x[0])
    tot = sum(w for _, w in pares)
    if tot <= 0:
        return None
    obj = (q / 100.0) * tot
    acc = 0.0
    for v, w in pares:
        acc += w
        if acc >= obj:
            return v
    return pares[-1][0]


def chk_salud(res, marg_doc):
    """6) % contributivo sintético (ponderado) por dpto vs marginal (±6pp)."""
    base = {"id": "6", "nombre": "Salud contributiva/dpto",
            "umbral": TOL_SALUD_PP, "umbral_str": f"±{TOL_SALUD_PP:.0f}pp"}
    ref = _pct_por_dpto(marg_doc, "salud_pct", "contributivo")
    if not ref:
        return {**base, "ok": False, "metrica": None, "metrica_str": "n/a",
                "detalle": "marginals.json sin salud_pct.contributivo", "fallas": -1}
    num, den = defaultdict(float), defaultdict(float)
    for p in res:
        dp = _dpto(campo(p, "dpto", "DPTO", "departamento", "dept", "cod_dpto"))
        if dp not in ref:
            continue
        w = _peso(p)
        den[dp] += w
        if _es_contributivo(campo(p, "regimen_salud", "regimen", "régimen", "salud",
                                  "tipo_salud", "afiliacion_salud", "P6090")):
            num[dp] += w
    obss, deltas = {}, {}
    for dp in sorted(ref):
        if den.get(dp, 0.0) <= 0:
            continue
        o = 100.0 * num[dp] / den[dp]
        obss[dp] = round(o, 2)
        deltas[dp] = round(o - ref[dp], 2)
    if not deltas:
        return {**base, "ok": False, "metrica": None, "metrica_str": "n/a",
                "detalle": "sin dptos comparables (no hay residentes de esos dptos)",
                "fallas": -1}
    m = max(abs(v) for v in deltas.values())
    ok = m <= TOL_SALUD_PP
    peor = max(deltas, key=lambda k: abs(deltas[k]))
    return {**base, "ok": ok, "metrica": round(m, 2), "metrica_str": f"{m:.1f}pp",
            "detalle": {"dptos": len(deltas), "peor_dpto": peor,
                        "observado_pct": obss,
                        "marginal_pct": {k: round(ref[k], 2) for k in deltas},
                        "delta_pp": deltas},
            "fallas": 0 if ok else 1}


def chk_urbano(res, marg_doc):
    """7) % urbano ponderado vs urbano_pct ±6pp (per-dpto si existe, si no nacional)."""
    base = {"id": "7", "nombre": "Urbano vs marginal",
            "umbral": TOL_URBANO_PP, "umbral_str": f"±{TOL_URBANO_PP:.0f}pp"}
    dptos_res = {_dpto(campo(p, "dpto", "DPTO", "departamento", "dept", "cod_dpto"))
                 for p in res}
    ref = {k: v for k, v in _pct_por_dpto(marg_doc, "urbano_pct").items()
           if k in dptos_res}
    esc = None
    if not ref:
        esc = _buscar_escalar(marg_doc, "urbano_pct")
        if esc is None:
            return {**base, "ok": False, "metrica": None, "metrica_str": "n/a",
                    "detalle": "marginals.json sin urbano_pct", "fallas": -1}
        esc = 100.0 * esc if 0.0 < esc <= 1.0 else esc
    num, den = defaultdict(float), defaultdict(float)
    for p in res:
        dp = _dpto(campo(p, "dpto", "DPTO", "departamento", "dept", "cod_dpto"))
        w = _peso(p)
        den[dp] += w
        if _es_urbano(campo(p, "clase", "CLASE", "tipo_clase", "area", "área",
                            "urbano_rural", "zona")):
            num[dp] += w
    if esc is not None:
        tot = sum(den.values())
        if tot <= 0:
            return {**base, "ok": False, "metrica": None, "metrica_str": "n/a",
                    "detalle": "sin pesos", "fallas": -1}
        obs = 100.0 * sum(num.values()) / tot
        obss = {"__nacional__": round(obs, 2)}
        margs = {"__nacional__": round(esc, 2)}
        deltas = {"__nacional__": round(obs - esc, 2)}
    else:
        obss, margs, deltas = {}, {}, {}
        for dp in sorted(ref):
            if den.get(dp, 0.0) <= 0:
                continue
            o = 100.0 * num[dp] / den[dp]
            obss[dp] = round(o, 2)
            margs[dp] = round(ref[dp], 2)
            deltas[dp] = round(o - ref[dp], 2)
        if not deltas:
            return {**base, "ok": False, "metrica": None, "metrica_str": "n/a",
                    "detalle": "sin dptos comparables (no hay residentes de esos dptos)",
                    "fallas": -1}
    m = max(abs(v) for v in deltas.values())
    ok = m <= TOL_URBANO_PP
    return {**base, "ok": ok, "metrica": round(m, 2), "metrica_str": f"{m:.1f}pp",
            "detalle": {"observado_pct": obss, "marginal_pct": margs,
                        "delta_pp": deltas},
            "fallas": 0 if ok else 1}


def chk_ingreso(res):
    """8) mediana nacional ponderada de ingreso_m>0 en 0,8-3 M y P99 < 60 M."""
    base = {"id": "8", "nombre": "Ingreso plausible",
            "umbral": [INGRESO_MEDIANA_MIN, INGRESO_MEDIANA_MAX],
            "umbral_str": "med .8-3M · P99<60M"}
    pares = []
    for p in res:
        v = _num(campo(p, "ingreso_m", "ingreso_mensual", "ingresos_m", "ingreso_mes",
                       "ingreso_mes_cop", "P6015"))
        if v is None or v <= 0:
            continue
        pares.append((v, _peso(p)))
    if not pares:
        return {**base, "ok": False, "metrica": None, "metrica_str": "n/a",
                "detalle": "sin registros con ingreso_m>0", "fallas": -1}
    med = _percentil_ponderado(pares, 50)
    p99 = _percentil_ponderado(pares, 99)
    if med is None or p99 is None:
        return {**base, "ok": False, "metrica": None, "metrica_str": "n/a",
                "detalle": "pesos no positivos", "fallas": -1}
    ok_med = INGRESO_MEDIANA_MIN <= med <= INGRESO_MEDIANA_MAX
    ok_p99 = p99 < INGRESO_P99_MAX
    ok = ok_med and ok_p99
    return {**base, "ok": ok, "metrica": round(med, 0),
            "metrica_str": f"{med/1e6:.2f}M·{p99/1e6:.1f}M",
            "detalle": {"mediana": round(med, 0), "p99": round(p99, 0),
                        "n_con_ingreso": len(pares), "mediana_ok": ok_med,
                        "p99_ok": ok_p99,
                        "rango_mediana": [INGRESO_MEDIANA_MIN, INGRESO_MEDIANA_MAX],
                        "p99_max": INGRESO_P99_MAX},
            "fallas": (0 if ok_med else 1) + (0 if ok_p99 else 1)}


def chk_compromiso_edad(res):
    """9) % opinador+militante en 60+ debe superar al de 18-29 (direccional)."""
    base = {"id": "9", "nombre": "Compromiso 60+ vs 18-29", "umbral": ">0",
            "umbral_str": "60+ > 18-29"}
    num = {"60+": 0.0, "18-29": 0.0}
    den = {"60+": 0.0, "18-29": 0.0}
    for p in res:
        edad = _num(campo(p, "edad", "P6040", "age"))
        if edad is None:
            continue
        grupo = "60+" if edad >= 60 else ("18-29" if 18 <= edad <= 29 else None)
        if grupo is None:
            continue
        w = _peso(p)
        den[grupo] += w
        if _es_activo(_cat_pol(campo(p, "compromiso_politico", "compromiso",
                                     "compromiso_pol", "compromisopolitico"))):
            num[grupo] += w
    if den["60+"] <= 0 or den["18-29"] <= 0:
        return {**base, "ok": False, "metrica": None, "metrica_str": "n/a",
                "detalle": "sin registros en 60+ o en 18-29", "fallas": -1}
    p60 = 100.0 * num["60+"] / den["60+"]
    p18 = 100.0 * num["18-29"] / den["18-29"]
    dif = p60 - p18
    ok = dif > 0
    return {**base, "ok": ok, "metrica": round(dif, 2), "metrica_str": f"{dif:+.1f}pp",
            "detalle": {"pct_60_mas": round(p60, 2), "pct_18_29": round(p18, 2),
                        "delta_pp": round(dif, 2),
                        "peso_60_mas": round(den["60+"], 1),
                        "peso_18_29": round(den["18-29"], 1)},
            "fallas": 0 if ok else 1}


# --- tabla / salida -----------------------------------------------------------
def _imprimir(checks, ok, n):
    ancho = 40
    print()
    print(f"validar_v2.py · residents_v2.json ({n} registros)")
    print("-" * 82)
    print(f"{'#':<2} {'CHECK':<{ancho}} {'ESTADO':<6} {'MÉTRICA':>12} {'UMBRAL':>12}")
    print("-" * 82)
    for c in checks:
        est = "OK" if c["ok"] else "FALLA"
        nom = c["nombre"][:ancho]
        print(f"{c['id']:<2} {nom:<{ancho}} {est:<6} {c['metrica_str']:>12} {c['umbral_str']:>12}")
    print("-" * 82)
    print(f"RESULTADO: {'TODO OK' if ok else 'FALLÓ'}")


def main():
    res_doc = _leer_json(RUTA_RESIDENTES)
    if res_doc is None:
        print(f"[error] no existe {RUTA_RESIDENTES.relative_to(RAIZ)}")
        return 1
    res = _residentes(res_doc)
    if not res:
        print("[error] residents_v2.json sin registros legibles")
        return 1

    marg_doc = _leer_json(RUTA_MARGINALES) or {}
    perf_doc = _leer_json(RUTA_PERFILES) or {}

    checks = [
        chk_piramide(res, marg_doc),
        chk_coherencia(res),
        chk_masa(res),
        chk_compromiso(res),
        chk_lean(res, perf_doc),
        chk_salud(res, marg_doc),
        chk_urbano(res, marg_doc),
        chk_ingreso(res),
        chk_compromiso_edad(res),
    ]
    ok = all(c["ok"] for c in checks)
    _imprimir(checks, ok, len(res))

    salida = {
        "generado": datetime.now(timezone.utc).isoformat(),
        "ok": ok,
        "n_residentes": len(res),
        "peso_total": round(sum(_num(campo(p, "peso", "weight", "fex", "FEX_C18"),
                                     0.0) or 0.0 for p in res), 1),
        "checks": checks,
    }
    RUTA_SALIDA.parent.mkdir(parents=True, exist_ok=True)
    with open(RUTA_SALIDA, "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)
    print(f"→ {RUTA_SALIDA}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
