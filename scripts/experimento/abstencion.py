# -*- coding: utf-8 -*-
"""
scripts/experimento/abstencion.py -- ABSTENCIÓN CALIBRADA ('no sé' = 99)
========================================================================

QUÉ HACE
    Inserta la opción 'no sabe / no responde' (código 99) en las respuestas de
    nuestras voces sintéticas, imitando CUÁNTO y CÓMO se abstienen los
    colombianos reales.

DE DÓNDE SALE LA TASA (lo más importante del módulo)
    La tasa de 'no sé' NO la decide el modelo: la decide el PERFIL demográfico
    de cada persona, calibrado contra datos humanos reales medidos en la
    ECP 2023 (n = 46.392 adultos, 99 ítems con opción 'no sabe'):

        tasa global mediana : 6.19 %
        por EDUCACIÓN       : bajo 9.75 % | medio 6.70 % | alto 4.01 %
                              (gradiente fuerte y monótono)
        por EDAD            : 18-29 6.41 % | 30-44 5.17 % | 45-59 5.39 % |
                              60+ 8.17 %   (forma de U)
        por ÍTEM            : la dificultad varía 16x (del 0.8 % al 12.9 %)

    El score de incertidumbre del modelo NO fija cuánta gente se abstiene:
    solo ORDENA, dentro de cada celda (educación x banda de edad), a quién le
    toca el 'no sé'. Todos los de una misma celda comparten la misma tasa y el
    modelo únicamente decide el orden dentro de la celda.

MODELO
        tasa = BASE * K * f_educación * f_edad
    con f_* = factor medido en la ECP (tasa del grupo / 6.19), renormalizado
    para que su media ponderada por los marginales de la ECP sea 1.0. Así
    (a) la media ponderada de propension(...) vuelve a dar la base 6.19 % y
    (b) las tasas relativas entre grupos son las que midió la ECP.

    NOTA DE CONSISTENCIA: 6.19 % es una mediana entre ítems y las tasas por
    educación también; con una marginal de educación realista las dos cifras no
    cierran al decimal. El módulo prioriza la base global (la invariante que
    fija el diseño) y deja la diferencia a la vista en
    reporte()['delta_vs_ecp']. Si se consiguen los marginales exactos,
    calibrar(pesos_educacion=..., pesos_edad=...) rehace los factores sin
    tocar nada más.

RIESGO A VIGILAR: SOBREABSTENCIÓN
    Meter 'no sé' cambia la distribución de los que SÍ contestan: si se
    abstiene más gente de la debida, la moda queda calculada sobre una
    submuestra sesgada, y justo en los ítems donde el modelo está más perdido
    (que suelen ser los que más información aportan). Por eso:
      * la tasa la fija el PERFIL, nunca el score;
      * escala_de_item() está acotada (0.4 - 2.2) y es una ESTIMACIÓN;
      * reporte() devuelve factor_vs_perfil; si se dispara (> 1.5 - 2.0) hay
        sobreabstención: revisar el ítem o bajar escala_item.

API
    propension(educacion, edad) -> float           tasa esperada en %
    aplicar(residentes, escala_item=1.0) -> list   agrega el campo 'final'
    escala_de_item(score_medio) -> float           modulador por dificultad
    reporte(res) -> dict                           tasas para comparar con la ECP

SIN DEPENDENCIAS externas: solo stdlib (el bloque __main__ usa json para
imprimir). Determinista: no usa random.
"""

# ---------------------------------------------------------------------------
# 1. CONSTANTES CALIBRADAS CONTRA LA ECP 2023
# ---------------------------------------------------------------------------
CODIGO_NO_SE = 99
BASE = 6.19        # % global mediano de 'no sé' (ECP 2023, n = 46.392)
MIN_CELDA = 8      # celdas más chicas usan la tasa global

# Marginales de la ECP (adultos 18+) usados para renormalizar los factores.
# SUPUESTO DOCUMENTADO: son una aproximación de las marginales reales; se
# pueden reemplazar sin tocar el resto del módulo (ver calibrar()).
PESOS_EDUCACION = {"bajo": 0.50, "medio": 0.28, "alto": 0.22}
PESOS_EDAD = {"18-29": 0.24, "30-44": 0.27, "45-59": 0.25, "60+": 0.24,
              "sin_dato": 0.0}

# Factores crudos = tasa medida del grupo / tasa global. Van como división
# para que la procedencia quede a la vista.
FACTOR_EDUCACION_RAW = {
    "bajo": 9.75 / BASE,
    "medio": 6.70 / BASE,
    "alto": 4.01 / BASE,
}
FACTOR_EDAD_RAW = {
    "18-29": 6.41 / BASE,
    "30-44": 5.17 / BASE,
    "45-59": 5.39 / BASE,
    "60+": 8.17 / BASE,
    "sin_dato": 1.0,          # sin edad no hay señal: factor neutro
}

GRUPOS_EDUCACION = ("bajo", "medio", "alto")
BANDAS_EDAD = ("18-29", "30-44", "45-59", "60+")

# Estado calibrado (lo llena calibrar() al importar).
FACTOR_EDUCACION = dict(FACTOR_EDUCACION_RAW)
FACTOR_EDAD = dict(FACTOR_EDAD_RAW)
K = 1.0


# ---------------------------------------------------------------------------
# 2. CALIBRACIÓN
# ---------------------------------------------------------------------------
def _normalizar_pesos(pesos):
    """Escala un diccionario de pesos para que sume 1.0 (devuelve copia)."""
    total = sum(pesos.values())
    if not total:
        return dict(pesos)
    return {k: v / total for k, v in pesos.items()}


def calibrar(pesos_educacion=None, pesos_edad=None):
    """Recalcula FACTOR_EDUCACION, FACTOR_EDAD y K. Se llama al importar.

    Con marginales que suman 1.0 y factores de media ponderada 1.0, K sale
    exactamente 1.0 (con marginales independientes la media del producto es el
    producto de las medias); el cálculo explícito es la guardia numérica de
    esa invariante.
    """
    global PESOS_EDUCACION, PESOS_EDAD, FACTOR_EDUCACION, FACTOR_EDAD, K

    if pesos_educacion is not None:
        PESOS_EDUCACION = _normalizar_pesos(pesos_educacion)
    if pesos_edad is not None:
        PESOS_EDAD = _normalizar_pesos(pesos_edad)
    PESOS_EDUCACION = _normalizar_pesos(PESOS_EDUCACION)
    PESOS_EDAD = _normalizar_pesos(PESOS_EDAD)

    media_e = sum(PESOS_EDUCACION.get(k, 0.0) * v
                  for k, v in FACTOR_EDUCACION_RAW.items())
    media_a = sum(PESOS_EDAD.get(k, 0.0) * v
                  for k, v in FACTOR_EDAD_RAW.items())

    FACTOR_EDUCACION = ({k: v / media_e for k, v in FACTOR_EDUCACION_RAW.items()}
                        if media_e else dict(FACTOR_EDUCACION_RAW))
    FACTOR_EDAD = ({k: v / media_a for k, v in FACTOR_EDAD_RAW.items()}
                   if media_a else dict(FACTOR_EDAD_RAW))

    esperanza = sum(PESOS_EDUCACION.get(k, 0.0) * PESOS_EDAD.get(j, 0.0)
                    * FACTOR_EDUCACION.get(k, 1.0) * FACTOR_EDAD.get(j, 1.0)
                    for k in PESOS_EDUCACION for j in PESOS_EDAD)
    K = (1.0 / esperanza) if esperanza else 1.0
    return FACTOR_EDUCACION, FACTOR_EDAD, K


calibrar()


# ---------------------------------------------------------------------------
# 3. PERFIL: EDUCACIÓN Y EDAD
# ---------------------------------------------------------------------------
EDUCACION_POR_DEFECTO = "medio"   # el factor más cercano a 1: mínima distorsión
EDAD_POR_DEFECTO = "sin_dato"

_EQUIV_EDUCACION = {
    # bajo = hasta secundaria
    "bajo": "bajo", "ninguna": "bajo", "ninguno": "bajo",
    "sin educacion": "bajo", "sin estudios": "bajo", "ningun grado": "bajo",
    "primaria": "bajo", "basica primaria": "bajo",
    "secundaria": "bajo", "basica secundaria": "bajo",
    "bachillerato incompleto": "bajo",
    # medio = media académica / bachillerato terminado
    "medio": "medio", "media": "medio", "media academica": "medio",
    "media tecnica": "medio", "bachiller": "medio", "bachillerato": "medio",
    # alto = superior
    "alto": "alto", "superior": "alto", "universitaria": "alto",
    "universitario": "alto", "profesional": "alto", "posgrado": "alto",
    "especializacion": "alto", "maestria": "alto", "doctorado": "alto",
}

_CLAVES_ALTO = ("superior", "universit", "posgrado", "profesional",
                "maestria", "doctorado", "especializacion")
_CLAVES_MEDIO = ("media", "bachiller")
_CLAVES_BAJO = ("ningun", "primaria", "secundaria", "basica", "sin estud")


def _normalizar_texto(valor):
    """minúsculas, sin acentos y sin puntuación, para comparar categorías."""
    if valor is None:
        return ""
    s = str(valor).strip().lower()
    for con, sin in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"),
                     ("ú", "u"), ("ü", "u"), ("ñ", "n")):
        s = s.replace(con, sin)
    for ch in ".,;:-_/":
        s = s.replace(ch, " ")
    return " ".join(s.split())


def grupo_educacion(educacion):
    """Mapea la educación de nuestros residentes a bajo / medio / alto.

    'ninguna', 'primaria' y 'secundaria' -> bajo | 'media' -> medio |
    'superior' -> alto. Lo que no se reconoce cae al grupo neutro ('medio'),
    que es el que menos distorsiona (factor más cercano a 1.0).
    """
    s = _normalizar_texto(educacion)
    if s in _EQUIV_EDUCACION:
        return _EQUIV_EDUCACION[s]
    if any(c in s for c in _CLAVES_ALTO):
        return "alto"
    if any(c in s for c in _CLAVES_MEDIO):
        return "medio"
    if any(c in s for c in _CLAVES_BAJO):
        return "bajo"
    return EDUCACION_POR_DEFECTO


def banda_edad(edad):
    """Banda de edad de la ECP: 18-29 | 30-44 | 45-59 | 60+.

    Acepta el número en años o la banda ya mapeada. Menores de 18 caen en
    18-29 (la ECP mide adultos) y los valores imposibles en 'sin_dato'.
    """
    if isinstance(edad, str) and edad in FACTOR_EDAD_RAW:
        return edad
    try:
        e = float(edad)
    except (TypeError, ValueError):
        return EDAD_POR_DEFECTO
    if e != e or e <= 0 or e > 120:      # NaN o valor imposible
        return EDAD_POR_DEFECTO
    if e < 30:
        return "18-29"
    if e < 45:
        return "30-44"
    if e < 60:
        return "45-59"
    return "60+"


# ---------------------------------------------------------------------------
# 4. PROPENSIÓN A ABSTENERSE
# ---------------------------------------------------------------------------
def _tasa_grupo(g_educacion, g_edad):
    """Tasa en % de una celda ya mapeada a grupos (sin escala de ítem)."""
    tasa = (BASE * K * FACTOR_EDUCACION.get(g_educacion, 1.0)
            * FACTOR_EDAD.get(g_edad, 1.0))
    return tasa if tasa > 0.0 else 0.0


def propension(educacion, edad):
    """Tasa esperada de 'no sé' (en %) para un perfil, según la ECP 2023.

    educacion: texto libre ('ninguna', 'primaria', 'secundaria', 'media',
               'superior', ...) o el grupo ya mapeado ('bajo'/'medio'/'alto').
    edad:      años (int/float/str numérico) o la banda ya mapeada.
    """
    return _tasa_grupo(grupo_educacion(educacion), banda_edad(edad))


# ---------------------------------------------------------------------------
# 5. DIFICULTAD DEL ÍTEM
# ---------------------------------------------------------------------------
ESCALA_ITEM_MIN = 0.4
ESCALA_ITEM_MAX = 2.2
PENDIENTE_ITEM = 2.4
SCORE_MEDIO_CENTRO = 0.25


def _acotar(valor, minimo, maximo):
    if valor < minimo:
        return minimo
    if valor > maximo:
        return maximo
    return valor


def escala_de_item(score_medio):
    """Modulador de la tasa por dificultad del ítem. ESTIMACIÓN, NO DATO.

    En la ECP la tasa por ítem varía 16x (0.8 % - 12.9 %), o sea que el ítem
    pesa tanto como el perfil. No conocemos la dificultad de una pregunta
    nueva, así que usamos la incertidumbre media que el propio modelo emite
    como proxy: más incertidumbre media -> ítem más difícil -> más 'no sé'.

    Recta centrada en 1.0 cuando el score medio es 0.25, pendiente 2.4, y
    acotada a [0.4, 2.2]: cubre todo el rango útil para scores medios entre
    0.0 y 0.75 y satura fuera de ahí, de modo que un ítem raro no pueda
    multiplicar la abstención por más de 2.2.
    """
    try:
        s = float(score_medio)
    except (TypeError, ValueError):
        return 1.0
    if s != s:                            # NaN
        return 1.0
    return _acotar(1.0 + PENDIENTE_ITEM * (s - SCORE_MEDIO_CENTRO),
                   ESCALA_ITEM_MIN, ESCALA_ITEM_MAX)


def _score(fila):
    """Score de incertidumbre de una voz; 0.0 si falta o viene mal."""
    if not isinstance(fila, dict):
        return 0.0
    try:
        v = float(fila.get("score"))
    except (TypeError, ValueError):
        return 0.0
    return v if v == v else 0.0


def _score_medio_de(residentes):
    """Score medio del lote (media aritmética, sin ponderar)."""
    if not residentes:
        return 0.0
    return sum(_score(f) for f in residentes) / float(len(residentes))


# ---------------------------------------------------------------------------
# 6. APLICAR LA ABSTENCIÓN
# ---------------------------------------------------------------------------
def aplicar(residentes, escala_item=1.0):
    """Mete el 'no sé' (99) según el perfil. Devuelve copia con 'final'.

    residentes: [{'id', 'educacion', 'edad', 'moda', 'score'}, ...]
    escala_item: modulador por dificultad del ítem (ver escala_de_item);
                 si es None se estima del score medio de la propia lista.

    Procedimiento (el del diseño, no se cambia):
      1. agrupa por celda = educación x banda de edad;
      2. dentro de la celda ordena por `score` DESCENDENTE;
      3. marca 99 a los primeros round(n_celda * propension/100 * escala);
      4. celdas con menos de MIN_CELDA personas usan la tasa global (6.19 %)
         en vez de la del perfil, para no sobreajustar celdas chicas.
    'final' queda en 99 o en la 'moda' original. No muta la entrada.
    """
    if escala_item is None:
        escala_item = escala_de_item(_score_medio_de(residentes))
    try:
        escala = float(escala_item)
    except (TypeError, ValueError):
        escala = 1.0
    if escala != escala or escala == float("inf"):
        escala = 1.0
    if escala < 0.0:
        escala = 0.0

    salida = []
    celdas = {}
    for i, r in enumerate(residentes):
        fila = dict(r)
        fila["final"] = fila.get("moda")
        salida.append(fila)
        celda = (grupo_educacion(fila.get("educacion")),
                 banda_edad(fila.get("edad")))
        celdas.setdefault(celda, []).append(i)

    puntajes = [_score(f) for f in salida]

    for (g_edu, g_edad), idxs in celdas.items():
        n = len(idxs)
        # celdas chicas: la tasa del perfil sería ruido sobre pocas personas
        tasa = _tasa_grupo(g_edu, g_edad) if n >= MIN_CELDA else BASE
        marcar = int(n * tasa * escala / 100.0 + 0.5)   # round() medio-arriba
        if marcar > n:
            marcar = n
        if marcar <= 0:
            continue
        # sorted es estable: los empates conservan el orden de entrada, así el
        # resultado es reproducible (este módulo no usa random).
        orden = sorted(idxs, key=lambda i: puntajes[i], reverse=True)
        for i in orden[:marcar]:
            salida[i]["final"] = CODIGO_NO_SE

    return salida


# ---------------------------------------------------------------------------
# 7. REPORTE PARA COMPARAR CONTRA LA ECP
# ---------------------------------------------------------------------------
REF_ECP = {
    "tasa_global": 6.19,
    "por_educacion": {"bajo": 9.75, "medio": 6.70, "alto": 4.01},
    "por_edad": {"18-29": 6.41, "30-44": 5.17, "45-59": 5.39, "60+": 8.17},
}


def _pct(parte, total):
    if not total:
        return 0.0
    return round(100.0 * parte / float(total), 2)


def _reparto(res, grupos, clave):
    """{grupo: tasa %} de 'no sé' en cada grupo (grupos fijos primero)."""
    agg = {g: [0, 0] for g in grupos}
    for fila in res:
        acum = agg.setdefault(clave(fila), [0, 0])
        acum[1] += 1
        if fila.get("final") == CODIGO_NO_SE:
            acum[0] += 1
    return {g: _pct(v[0], v[1]) for g, v in agg.items()}


def reporte(res):
    """Tasas resultantes, para compararlas contra la ECP.

    Devuelve:
      n, n_no_se, tasa_global (%),
      por_educacion / por_edad (% de 'no sé' por grupo),
      esperado_por_perfil: lo que el perfil predice para ESTA muestra,
      factor_vs_perfil: tasa_global / esperado_por_perfil (si se dispara,
          > 1.5 - 2.0, hay sobreabstención),
      referencia_ecp y delta_vs_ecp (modelo - ECP, en puntos porcentuales).
    """
    n = len(res)
    n_no_se = sum(1 for f in res if f.get("final") == CODIGO_NO_SE)
    tasa_global = _pct(n_no_se, n)
    por_educacion = _reparto(res, GRUPOS_EDUCACION,
                             lambda f: grupo_educacion(f.get("educacion")))
    por_edad = _reparto(res, BANDAS_EDAD,
                        lambda f: banda_edad(f.get("edad")))

    esperado = 0.0
    for f in res:
        esperado += _tasa_grupo(grupo_educacion(f.get("educacion")),
                                banda_edad(f.get("edad")))
    esperado = (esperado / n) if n else 0.0
    factor = round(tasa_global / esperado, 2) if esperado > 0 else 0.0

    delta = {
        "tasa_global": round(tasa_global - REF_ECP["tasa_global"], 2),
        "por_educacion": {g: round(por_educacion[g] - REF_ECP["por_educacion"][g], 2)
                          for g in REF_ECP["por_educacion"] if g in por_educacion},
        "por_edad": {g: round(por_edad[g] - REF_ECP["por_edad"][g], 2)
                     for g in REF_ECP["por_edad"] if g in por_edad},
    }

    return {
        "n": n,
        "n_no_se": n_no_se,
        "tasa_global": tasa_global,
        "por_educacion": por_educacion,
        "por_edad": por_edad,
        "esperado_por_perfil": round(esperado, 2),
        "factor_vs_perfil": factor,
        "referencia_ecp": REF_ECP,
        "delta_vs_ecp": delta,
    }


# ---------------------------------------------------------------------------
# 8. DEMO DETERMINISTA -- python scripts/experimento/abstencion.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import json

    EDUCACIONES = ["ninguna", "primaria", "secundaria", "media", "superior",
                   "tecnico"]
    voces = []
    for i in range(600):
        voces.append({
            "id": "v%04d" % i,
            "educacion": EDUCACIONES[i % len(EDUCACIONES)],
            "edad": 18 + (i * 7) % 60,
            "moda": 1 + (i % 4),
            "score": ((i * 37) % 101) / 100.0,
        })

    media = _score_medio_de(voces)
    print("score medio del lote: %.3f -> escala de ítem %.2f"
          % (media, escala_de_item(media)))
    print(json.dumps(reporte(aplicar(voces, escala_item=None)),
                     ensure_ascii=False, indent=2, sort_keys=True))

    # celda chica (n=5 < MIN_CELDA): debe usar la tasa global, no la del perfil
    chicas = [{"id": "c%d" % i, "educacion": "superior", "edad": 25,
               "moda": 2, "score": 0.90 - 0.10 * i} for i in range(5)]
    for esc in (1.0, 2.2):
        marcados = sum(1 for f in aplicar(chicas, escala_item=esc)
                       if f["final"] == CODIGO_NO_SE)
        print("celda chica n=5 (superior 18-29), escala_item=%.1f -> %d con 99 "
              "[global %.2f %% | perfil %.2f %%]"
              % (esc, marcados, BASE, propension("superior", "18-29")))
