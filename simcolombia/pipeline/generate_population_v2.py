#!/usr/bin/env python3
"""Genera los residentes sintéticos v2 → web/residents_v2.json.

Muestreo CONJUNTO del pool GEIH: edad, sexo, educación, clase, ingreso y oficio
CIUO-08 salen de UNA misma persona real (fin de la abuela albañil). n por dpto
∝ población real con piso 80 y `peso` para agregar. Ejes políticos por hash
determinista. Seed fija random.Random(2026_09_21): la demo es reproducible.
Solo stdlib (gzip/json/csv-free, sin pandas).
"""
import gzip
import hashlib
import json
import os
import random
import unicodedata
from bisect import bisect_left
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent          # simcolombia/
DASH = BASE.parent / "web"   # el sitio desplegado lee de aquí
DASH.mkdir(parents=True, exist_ok=True)

rng = random.Random(2026_09_21)
N_TOTAL = int(os.environ.get("SIM_N", "8000"))
PISO_DPTO = 80
ANIO = int(os.environ.get("SIM_ANIO", os.environ.get("AÑO_SIM", "2026")))
DESPLAZAMIENTO = ANIO - 2026
AVISOS = []

# ───────────── banco nacional de nombres (idéntico al v1) ─────────────
NOMBRES = {
 "mujer": {
  "mayor": ["Carmen", "Blanca", "Rosa", "Ana", "Gloria", "Cecilia", "Myriam", "Teresa",
    "Lucía", "Inés", "Fanny", "Stella", "Ligia", "Alba", "Nubia", "Elvia", "Graciela",
    "Aura", "Mercedes", "Josefina", "Bertha", "Amparo", "Leonor", "Edilma", "Omaira"],
  "adulta": ["Sandra", "Patricia", "Claudia", "Martha", "Luz", "Diana", "Adriana",
    "Mónica", "Yolanda", "Esperanza", "Marcela", "Paola", "Carolina", "Liliana",
    "Johanna", "Yaneth", "Milena", "Amanda", "Nancy", "Doris", "Consuelo", "Pilar",
    "Yadira", "Rocío", "Maritza", "Zoraida", "Yesenia", "Katherine", "Viviana", "Erika"],
  "joven": ["Camila", "Valentina", "Daniela", "Laura", "Alejandra", "Natalia", "Karen",
    "Angie", "Paula", "Juliana", "Gabriela", "Isabella", "Mariana", "Sara", "Luisa",
    "Manuela", "Salomé", "Danna", "Valeria", "Sofía", "Nicoll", "Dayana", "Michelle"],
  "nina": ["Emma", "Luciana", "Antonella", "Emily", "Samantha", "Guadalupe", "Celeste",
    "Amelia", "Julieta", "Violeta", "Maité", "Alaia"]},
 "hombre": {
  "mayor": ["José", "Luis", "Jorge", "Pedro", "Rafael", "Gustavo", "Hernando", "Álvaro",
    "Jaime", "Humberto", "Gilberto", "Marco", "Alfonso", "Ramiro", "Guillermo", "Ernesto",
    "Aníbal", "Efraín", "Gonzalo", "Reinaldo", "Campo Elías", "Misael", "Belisario"],
  "adulto": ["Carlos", "Juan", "Andrés", "Fernando", "Óscar", "Mauricio", "Javier",
    "Wilson", "Fredy", "Édgar", "Fabián", "Henry", "Nelson", "Jhon", "Alexander",
    "Leonardo", "Ricardo", "Diego", "Iván", "Milton", "Norbey", "Arley", "Wilmer",
    "Yeison", "Duván", "Éder", "Robinson", "Hugo", "Elkin", "Julián"],
  "joven": ["Santiago", "Sebastián", "Nicolás", "Samuel", "Mateo", "Daniel", "David",
    "Felipe", "Miguel", "Cristian", "Brayan", "Kevin", "Esteban", "Tomás", "Emmanuel",
    "Juan José", "Alejandro", "Simón", "Jerónimo", "Dilan", "Stiven", "Camilo"],
  "nino": ["Matías", "Thiago", "Liam", "Emiliano", "Maximiliano", "Salvador", "Gael",
    "Benjamín", "Josué", "Ian", "Dylan", "Martín"]},
}
COMPUESTOS = {"mujer": ["María", "Ana", "Luz", "Leidy", "Ingrid", "Lina"],
              "hombre": ["Juan", "Luis", "Carlos", "José", "Jhon", "Miguel"]}
APELLIDOS = ["Rodríguez", "Martínez", "García", "López", "González", "Hernández",
 "Sánchez", "Ramírez", "Pérez", "Díaz", "Muñoz", "Rojas", "Moreno", "Jiménez", "Gutiérrez",
 "Torres", "Vargas", "Castro", "Ruiz", "Álvarez", "Romero", "Suárez", "Gómez", "Ortiz",
 "Cárdenas", "Guerrero", "Rincón", "Castillo", "Mejía", "Restrepo", "Valencia", "Ospina",
 "Cardona", "Zapata", "Montoya", "Arias", "Betancur", "Agudelo", "Giraldo", "Salazar",
 "Palacios", "Mosquera", "Córdoba", "Machado", "Julio", "De la Hoz", "Barrios", "Pacheco",
 "Fontalvo", "Cantillo", "Navarro", "Meza", "Acosta", "Padilla", "Bolaños", "Chamorro",
 "Delgado", "Ceballos", "Paz", "Riascos", "Quintero", "Henao", "Uribe", "Vélez", "Parra",
 "Prieto", "Bonilla", "Cortés", "Reyes", "Molina", "Camacho", "Contreras", "Silva"]


def cohorte(edad, sexo):
    key = ("mayor" if edad >= 60 else "adulta" if edad >= 30 else
           "joven" if edad >= 13 else "nina")
    if sexo == "hombre":
        key = {"adulta": "adulto", "nina": "nino"}.get(key, key)
    return NOMBRES[sexo][key]


def nombre_pila(edad, sexo, regionales):
    # el banco está indexado por edad EN 2026: se reindexa a cohorte de nacimiento
    edad_cohorte = max(0, edad - DESPLAZAMIENTO)
    if regionales and rng.random() < 0.15:
        cand = rng.choice(regionales)
        if cand.isalpha() and len(cand) <= 11:
            return cand
    base = rng.choice(cohorte(edad_cohorte, sexo))
    if edad >= 13 and rng.random() < 0.33:  # compuestos: María Fernanda, Luis Alberto
        pre = rng.choice(COMPUESTOS[sexo])
        if pre != base and not base.count(" "):
            return f"{pre} {base}"
    return base


# ───────────── utilidades ─────────────
def _hash(clave, sal):
    """Entero determinista y reproducible desde la llave (id*37 del v1)."""
    return int(hashlib.sha256(f"{sal}|{clave}".encode("utf-8")).hexdigest()[:12], 16)


def sample_w(pairs, r=None):
    """Ruleta por peso; None si todos los pesos son <= 0."""
    r = r or rng
    pairs = [(v, w) for v, w in pairs if w and w > 0]
    if not pairs:
        return None
    total = sum(w for _, w in pairs)
    x = r.uniform(0, total)
    for v, w in pairs:
        x -= w
        if x <= 0:
            return v
    return pairs[-1][0]


def _get(rec, *claves, default=None):
    for k in claves:
        if k in rec and rec[k] not in (None, "", " "):
            return rec[k]
    return default


def _num(v, default=None):
    if v is None:
        return default
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(",", "").replace("$", "").replace(" ", "")
    if not s:
        return default
    try:
        return float(s)
    except ValueError:
        return default


def norm_txt(s):
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.strip().upper()


def cod_norm(x):
    s = str(x).strip()
    return s.zfill(2) if s.isdigit() and len(s) <= 2 else s


def _norm_sexo(v):
    s = str(v).strip().lower()
    if s in ("1", "hombre", "h", "masculino", "masc"):
        return "hombre"
    if s in ("2", "mujer", "femenino", "fem"):
        return "mujer"
    if s.startswith("h"):
        return "hombre"
    if s.startswith("mu") or s.startswith("f"):
        return "mujer"
    return "hombre"


EDU_NUM = {1: "ninguna", 2: "ninguna", 3: "primaria", 4: "secundaria", 5: "media",
           6: "media", 7: "media", 8: "superior", 9: "superior", 10: "superior",
           11: "superior", 12: "superior", 13: "superior"}


def _norm_educacion(v):
    if v is None:
        return "ninguna"
    if isinstance(v, (int, float)):
        return EDU_NUM.get(int(v), "superior")
    s = str(v).strip().lower()
    if s in ("ninguna", "primaria", "secundaria", "media", "técnica", "superior"):
        return s
    if not s or "ningun" in s or "preescolar" in s:
        return "ninguna"
    if "primar" in s:
        return "primaria"
    if "secund" in s or "bachiller" in s:
        return "secundaria"
    if "media" in s:
        return "media"
    if "técnic" in s or "tecnic" in s or "tecnológ" in s:
        return "técnica"
    if any(k in s for k in ("superior", "universit", "profesional", "postgrado",
                            "maestr", "doctor")):
        return "superior"
    return "media"


def _norm_clase(v):
    s = str(v).strip().lower()
    if s in ("1", "cabecera", "urbano", "urbana"):
        return "cabecera"
    if s in ("2", "resto", "rural"):
        return "resto"
    return s or "cabecera"


def poblacion_de(d):
    for k in ("poblacion", "población", "pob", "total"):
        if d.get(k):
            try:
                return float(d[k])
            except (TypeError, ValueError):
                pass
    if d.get("sexo"):
        return float(sum(d["sexo"].values()))
    if d.get("edad"):
        return float(sum(d["edad"].values()))
    return 1.0


def asignar_n(pesos, total, piso):
    """n por dpto ∝ peso con piso; reparte el residuo por mayor resto."""
    cods = list(pesos)
    n = {c: piso for c in cods}
    restante = max(0, total - piso * len(cods))
    tp = sum(max(pesos[c], 0.0) for c in cods) or 1.0
    crudo = {c: restante * max(pesos[c], 0.0) / tp for c in cods}
    for c in cods:
        n[c] += int(crudo[c])
    falta = total - sum(n.values())
    orden = sorted(cods, key=lambda c: -(crudo[c] - int(crudo[c])))
    i = 0
    while falta > 0 and orden:
        n[orden[i % len(orden)]] += 1
        i += 1
        falta -= 1
    while falta < 0:
        c = max(cods, key=lambda c: n[c])
        if n[c] <= piso:
            break
        n[c] -= 1
        falta += 1
    return n


# AREA de la GEIH → la ciudad principal (o su área metropolitana) donde vive la
# persona. Es dato real del registro; vacío = otro municipio del departamento.
CIUDAD_GEIH = {"05": "Medellín", "08": "Barranquilla", "11": "Bogotá", "13": "Cartagena", "15": "Tunja",
    "17": "Manizales", "18": "Florencia", "19": "Popayán", "20": "Valledupar", "23": "Montería", "27": "Quibdó",
    "41": "Neiva", "44": "Riohacha", "47": "Santa Marta", "50": "Villavicencio", "52": "Pasto", "54": "Cúcuta",
    "63": "Armenia", "66": "Pereira", "68": "Bucaramanga", "70": "Sincelejo", "73": "Ibagué", "76": "Cali",
    "81": "Arauca", "85": "Yopal", "86": "Mocoa", "88": "San Andrés", "91": "Leticia", "94": "Inírida",
    "95": "San José del Guaviare", "97": "Mitú", "99": "Puerto Carreño"}


def _grupo(edad):
    if edad >= 85:
        return "85+"
    lo = (edad // 5) * 5
    return f"{lo}-{lo + 4}"


def _nombres_regionales(cod):
    """(5) Nombres frecuentes del dossier del dpto (DOSSIERS o archivo); [] si no hay."""
    cache = _nombres_regionales.__dict__.setdefault("_cache", {})
    if cod in cache:
        return cache[cod]
    dossier = None
    dossiers = globals().get("DOSSIERS")
    if isinstance(dossiers, dict):
        dossier = dossiers.get(cod) or dossiers.get(cod_norm(cod))
    if dossier is None:
        for cand in (BASE / "data" / "dossiers" / f"{cod}.json",
                     BASE / "data" / f"dossier_{cod}.json"):
            if cand.exists():
                try:
                    dossier = json.loads(cand.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    dossier = None
                break
    if isinstance(dossier, dict) and isinstance(dossier.get("dossier"), dict):
        dossier = dossier["dossier"]
    nm = dossier.get("nombres_frecuentes") if isinstance(dossier, dict) else None
    reg = [str(x) for x in nm if str(x).strip()] if isinstance(nm, list) else []
    cache[cod] = reg
    return reg


# ───────────── CIUO-08: 2 primeros dígitos → oficio legible (Colombia) ─────────────
CIUO = {
 "11": "director(a) y alto(a) funcionario(a)",
 "12": "director(a) administrativo(a) o comercial",
 "13": "director(a) de producción y operaciones",
 "14": "gerente de comercio, hotel o restaurante",
 "21": "profesional de ingeniería o ciencias",
 "22": "profesional de la salud",
 "23": "docente",
 "24": "administrador(a) o contador(a)",
 "25": "especialista en sistemas (TIC)",
 "26": "abogado(a) o profesional social",
 "31": "técnico(a) en ingeniería",
 "32": "técnico(a) de la salud",
 "33": "técnico(a) administrativo(a) o financiero(a)",
 "34": "técnico(a) en servicios de protección",
 "35": "técnico(a) de sistemas (TIC)",
 "41": "empleado(a) de oficina",
 "42": "recepcionista o atención al público",
 "43": "auxiliar contable o de datos",
 "44": "auxiliar administrativo(a)",
 "51": "cocinero(a), mesero(a) o peluquero(a)",
 "52": "vendedor(a) de comercio",
 "53": "cuidador(a) de personas",
 "54": "vigilante o personal de protección",
 "61": "agricultor(a) o trabajador(a) agropecuario(a)",
 "62": "jornalero(a) agropecuario(a)",
 "63": "pescador(a) o recolector(a)",
 "71": "albañil u oficial de construcción",
 "72": "mecánico(a) o trabajador(a) del metal",
 "73": "artesano(a)",
 "74": "electricista o técnico(a) electrónico(a)",
 "75": "operario(a) de manufactura",
 "81": "operador(a) de máquina fija",
 "82": "ensamblador(a)",
 "83": "conductor(a)",
 "91": "limpiador(a) o servicio doméstico",
 "92": "peón agropecuario(a)",
 "93": "peón de construcción o minería",
 "94": "ayudante de cocina",
 "95": "vendedor(a) ambulante",
 "96": "recolector(a) de desechos o aseo",
}
CIUO_1 = {  # respaldo por gran grupo cuando el código viene truncado
 "1": "directivo(a) o funcionario(a)",
 "2": "profesional",
 "3": "técnico(a)",
 "4": "empleado(a) de oficina",
 "5": "trabajador(a) de servicios y ventas",
 "6": "trabajador(a) agropecuario(a)",
 "7": "oficial de oficios y construcción",
 "8": "operador(a) de máquinas",
 "9": "trabajador(a) elemental",
}
ESFUERZO = {"61", "62", "63", "71", "72", "73", "74", "75", "81", "82", "83",
            "91", "92", "93", "94", "95", "96"}


def _sin_oficio(edad, educacion, rid, clase="cabecera"):
    """Oficio de reserva cuando el pool no trae CIUO (regla por edad + hash)."""
    if edad < 6:
        return "primera infancia"
    if edad < 18:
        return "estudiante"
    h = _hash(rid, "ocio") & 1
    if edad >= 62:
        # (1) pensión con TOPE: ~28% de los 62+ sin oficio, sesgada a educación
        # media/superior y clase urbana (lotería determinista por hash).
        prob = 0.24
        if educacion in ("superior", "media"):
            prob += 0.10
        if educacion == "ninguna":
            prob -= 0.12
        prob += 0.06 if clase == "cabecera" else -0.10
        prob = min(max(prob, 0.0), 0.6)
        if (_hash(rid, "pension") % 1000) / 1000.0 < prob:
            return "pensionado(a)"
        return "oficios del hogar" if h else "inactivo(a)"
    return "buscando trabajo" if h else "oficios del hogar"


def oficio_de(ciuo, edad, educacion, rid, clase="cabecera"):
    """Devuelve (oficio legible, código de 2 dígitos o None)."""
    if ciuo not in (None, "", " "):
        digits = "".join(ch for ch in str(ciuo) if ch.isdigit())
        dos = digits[:2] if len(digits) >= 2 else (digits or "")
        oc = CIUO.get(dos) or CIUO_1.get(dos[:1])
        if oc:
            if edad > 85 and dos in ESFUERZO:   # anti-absurdo: >85 no hace esfuerzo físico
                return _sin_oficio(edad, educacion, rid, clase), dos
            return oc, dos
    return _sin_oficio(edad, educacion, rid, clase), None


# ───────────── carga de insumos ─────────────
def cargar_marginals():
    data = json.loads((BASE / "data" / "marginals.json").read_text(encoding="utf-8"))
    if isinstance(data, dict) and "departamentos" in data:
        data = data["departamentos"]
    return data


def cargar_pool():
    p = BASE / "data" / "pool_geih.json.gz"
    if not p.exists():
        return {}
    with gzip.open(p, "rt", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        for k in ("pool", "departamentos", "por_dpto", "dptos"):
            if isinstance(data.get(k), dict):
                data = data[k]
                break
    pool = {}
    if isinstance(data, dict):
        for cod, lst in data.items():
            if isinstance(lst, list):
                pool[cod_norm(cod)] = lst
            elif isinstance(lst, dict) and isinstance(lst.get("registros"), list):
                pool[cod_norm(cod)] = lst["registros"]
    elif isinstance(data, list):
        for r in data:
            cod = cod_norm(_get(r, "dpto", "DPTO", "cod_dpto", default=""))
            pool.setdefault(cod, []).append(r)
    return pool


def cargar_perfiles(marg):
    p = BASE / "data" / "perfiles_politicos_2018.json"
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data.get("perfiles_politicos_2018", data)
        except (json.JSONDecodeError, OSError):
            pass
    out = {}
    if isinstance(marg, dict) and isinstance(marg.get("perfiles_politicos_2018"), dict):
        out.update(marg["perfiles_politicos_2018"])
    for k, d in (marg or {}).items():
        if isinstance(d, dict):
            nombre = norm_txt(d.get("nombre", k))
            if "lean_2018" in d:
                out[nombre] = d
            elif "perfiles_politicos_2018" in d:
                out[nombre] = d["perfiles_politicos_2018"]
    return out


def pool_sintetico(dep):
    """Sin pool real: registros gruesos para que la demo no muera (queda en AVISOS)."""
    pool = {}
    for cod, d in dep.items():
        edu = d.get("educacion_pct") or {"primaria": 35, "secundaria": 30,
                                         "media": 20, "superior": 15}
        recs = []
        for _ in range(160):
            recs.append({
                "edad": rng.randint(15, 88),
                "sexo": rng.choice(["hombre", "mujer"]),
                "educacion": sample_w(list(edu.items())) or "secundaria",
                "clase": rng.choice([1, 2]),
                "ingreso": rng.choice([0, 1_200_000, 1_900_000, 2_600_000, 0]),
                "fex": 1.0, "oficio_ciuo": None,
            })
        pool[cod] = recs
    return pool


def muestrear(recs, n):
    """Muestreo con reemplazo ∝ fex (determinista por la seed global)."""
    fex = [max(_num(_get(r, "fex", "FEX_C18", "fex_c18", "FEX"), 1.0) or 0.0, 0.0)
           for r in recs]
    total = sum(fex)
    if total <= 0:
        return [rng.choice(recs) for _ in range(n)]
    acum, s = [], 0.0
    for w in fex:
        s += w
        acum.append(s)
    out = []
    for _ in range(n):
        x = rng.uniform(0, total)
        i = bisect_left(acum, x)
        out.append(recs[i if i < len(recs) else len(recs) - 1])
    return out


# ───────────── ejes políticos (deterministas por hash) ─────────────
FALLBACK_LEAN = {"centro_tradicional": 20.0, "derecha_uribismo": 20.0,
                 "izquierda": 20.0, "verdes_alternativos": 20.0,
                 "otros_blanco_nulo": 20.0}


COMPROMISO_PESOS = {
    "18-29": (("indiferente", 34), ("desencantado", 30), ("opinador", 24), ("militante", 12)),
    "30-59": (("indiferente", 25), ("desencantado", 32), ("opinador", 29), ("militante", 14)),
    "60+":   (("indiferente", 15), ("desencantado", 26), ("opinador", 38), ("militante", 21)),
}


def tramo_edad(edad):
    return "18-29" if edad < 30 else ("30-59" if edad < 60 else "60+")


def elegir_compromiso(rid, edad):
    """(2) Pesos por tramo de edad; el agregado se mantiene ≈ 25/30/30/15."""
    b = _hash(rid, 37) % 1000
    acum = 0
    for etiqueta, w in COMPROMISO_PESOS[tramo_edad(edad)]:
        acum += w * 10
        if b < acum:
            return etiqueta
    return COMPROMISO_PESOS[tramo_edad(edad)][-1][0]


def elegir_lean(perfil, r):
    """Familia política por ruleta con los pct de perfiles_politicos_2018."""
    lp = None
    if isinstance(perfil, dict):
        lp = perfil.get("lean_2018") or perfil.get("lean") or perfil
    if not isinstance(lp, dict) or not lp:
        lp = FALLBACK_LEAN
    familias = [k for k, v in lp.items() if _num(v, 0) and _num(v, 0) > 0]
    if not familias:
        return r.choice(list(FALLBACK_LEAN))
    return sample_w([(k, lp[k]) for k in familias], r=r) or familias[0]


# ───────────── generación ─────────────
M = cargar_marginals()
DEP = {cod_norm(k): d for k, d in M.items()}
POOL = cargar_pool()
PERFILES = cargar_perfiles(M)
if not POOL:
    AVISOS.append("pool_geih.json.gz ausente o vacío: se sintetiza el pool (demo)")
    POOL = pool_sintetico(DEP)

pesos = {c: poblacion_de(d) for c, d in DEP.items()}
n_dpto = asignar_n(pesos, N_TOTAL, PISO_DPTO)

RES, CIUO_RES = [], []
for cod in sorted(DEP):
    d = DEP[cod]
    nombre_dpto = d.get("nombre", cod)
    n = n_dpto[cod]
    peso = poblacion_de(d) / n if n else 0.0
    recs = POOL.get(cod) or POOL.get(cod_norm(cod)) or []
    if not recs:
        AVISOS.append(f"sin registros de pool para {cod}: se sintetiza")
        recs = pool_sintetico({cod: d}).get(cod, [])
    perfil = (PERFILES.get(norm_txt(nombre_dpto)) or PERFILES.get(cod)
              or PERFILES.get(cod_norm(cod)) or {})
    sal = d.get("salud_pct") or {}
    muestras = muestrear(recs, n)
    regionales = _nombres_regionales(cod)
    # (3) dos etapas: cuota del marginal por dpto y, dentro de la cuota, contributivo
    # a los mayores ingresos/formales (jitter de hash desempata); subsidiado al resto.
    contributivos = set()
    if sal:
        tot_sal = sum(max(_num(v, 0), 0) for v in sal.values()) or 1.0
        pct_contrib = sum(max(_num(v, 0), 0) for k, v in sal.items()
                          if "contribut" in str(k).lower()) / tot_sal
        cuota = max(0, min(n, int(round(n * pct_contrib))))
        contributivos = set(sorted(
            range(n),
            key=lambda j: (_num(_get(muestras[j], "ingreso", "INGLABO",
                                     "ingreso_laboral"), 0) or 0)
            + (400_000 if _get(muestras[j], "formal", "P6450") in (1, "1", True) else 0)
            + (_hash(f"{cod}-{j}", "salud") % 200_000),
            reverse=True)[:cuota])
    for i, r in enumerate(muestras):
        rid = f"{cod}-{i:03d}"
        edad = int(_num(_get(r, "edad", "P6040", default=30), 30))
        sexo = _norm_sexo(_get(r, "sexo", "P3271", default="mujer"))
        educacion = _norm_educacion(_get(r, "educacion", "P3042", default="secundaria"))
        clase = _norm_clase(_get(r, "clase", "CLASE", default=1))
        ingreso = _num(_get(r, "ingreso", "INGLABO", "ingreso_laboral"))
        ciuo = _get(r, "oficio_ciuo", "oficio", "OFICIO_C8", "ciuo")
        ocupacion, cod2 = oficio_de(ciuo, edad, educacion, rid, clase)
        # anti-absurdo: un grupo profesional (CIUO 21-26) exige educación superior
        if educacion == "ninguna" and cod2 and cod2.isdigit() and 21 <= int(cod2) <= 26:
            AVISOS.append(f"{rid}: {ocupacion} con educación 'ninguna' en el pool → superior")
            educacion = "superior"
        if sal:
            regimen = "contributivo" if i in contributivos else "subsidiado"
        else:
            regimen = "contributivo" if (ingreso and ingreso > 1_400_000) else "subsidiado"
        # (4) 0 = sin ingreso (se muestra 0) · None = no aplica · redondeo a decenas de mil.
        ingreso_m = int(round(ingreso / 100_000.0) * 100_000) if ingreso is not None else None
        RES.append({
            "id": rid,
            "nombre": f"{nombre_pila(edad, sexo, regionales)} {rng.choice(APELLIDOS)} {rng.choice(APELLIDOS)}",
            "edad": edad,
            "sexo": sexo,
            "dpto": cod,
            "dpto_nombre": nombre_dpto,
            "ocupacion": ocupacion,
            "educacion": educacion,
            "regimen_salud": regimen,
            "grupo_edad": _grupo(edad),
            "clase": clase,
            "peso": round(peso, 3),
            "compromiso": elegir_compromiso(rid, edad),
            "lean": elegir_lean(perfil, random.Random(_hash(rid, "lean"))),
            "ingreso_m": ingreso_m,
            "origen": "geih",
            "ciudad_geih": CIUDAD_GEIH.get(cod_norm(_get(r, "area", "AREA", default="") or "")) if _get(r, "area", "AREA", default=None) else None,
        })
        CIUO_RES.append(cod2)

# ───────────── resumen + spot-check anti-absurdo ─────────────
nd = Counter(r["dpto"] for r in RES)
print(f"\n{len(RES)} residentes · {len(DEP)} dptos · N objetivo {N_TOTAL} · seed 2026_09_21")
print(f"n por dpto: min {min(nd.values())} / max {max(nd.values())} (piso {PISO_DPTO})")
tot = len(RES) or 1
comp = Counter(r["compromiso"] for r in RES)
print("compromiso: " + " · ".join(f"{k} {v / tot * 100:.1f}%" for k, v in comp.most_common()))
fis = sum(1 for r, c in zip(RES, CIUO_RES) if r["edad"] > 85 and c in ESFUERZO)
doc = sum(1 for r in RES if r["ocupacion"] == "docente" and r["educacion"] == "ninguna")
print(f"anti-absurdo: >85 en esfuerzo físico = {fis} (esperado ~0) · "
      f"docentes con educación 'ninguna' = {doc} (esperado 0)")
if AVISOS:
    print("avisos: " + " | ".join(AVISOS[:6]) + (" ..." if len(AVISOS) > 6 else ""))

# ── Cobertura GEIH: en dptos amazónicos la GEIH solo encuesta cabeceras.
# Imputamos la cuota rural del marginal DANE (urbano_pct) reasignando clase
# determinista, priorizando perfiles plausiblemente rurales.
_RURALES = ("agricultor", "agropec", "peón", "peon", "pesca", "minería", "mineria",
            "oficios del hogar", "inactivo", "buscando")
from collections import defaultdict as _dd
_por = _dd(list)
for _r in RES:
    _por[_r["dpto"]].append(_r)
for _cod, _grupo in _por.items():
    _upct = (M.get(_cod) or {}).get("urbano_pct")
    if _upct is None:
        continue
    _urb = [x for x in _grupo if x.get("clase") == "cabecera"]
    _obs = 100.0 * len(_urb) / len(_grupo)
    if _obs - _upct <= 6.0:
        continue
    _n = int(round((_obs - _upct) / 100.0 * len(_grupo)))
    def _prio(x):
        o = (x.get("ocupacion") or "").lower()
        h = 0
        for c in x["id"]:
            h = (h * 31 + ord(c)) & 0xFFFFFFFF
        return (0 if any(k in o for k in _RURALES) else 1, h)
    for x in sorted(_urb, key=_prio)[:_n]:
        x["clase"] = "resto"

out = DASH / "residents_v2.json"
json.dump(RES, out.open("w", encoding="utf-8"), ensure_ascii=False)
print(f"→ {out}")
