#!/usr/bin/env python3
"""SHOWTIME — el gatillo de los $100. Fable 5.1 sobre Sim Colombia.

Todo precableado: la noche del evento solo se corre esto.

  uv run --project orchestrator python simcolombia/fable/showtime.py ping
  ...                                                          pais serialize
  ...                                                          pais "¿pregunta?"
  ...                                                          pais 2050
  ...                                                          preguntar   (micrófono: preguntas por input, sin shell)
  ...                                                          replay <acto>  (re-muestra un acto ya corrido, gratis)
  ...                                                          auditor
  ...                                                          forense
  ...                                                          duelo
  ...                                                          d2050

Requisitos: FABLE_ENABLED=1 en .env (la key y el workspace ya están).
Economía: corpus del país se paga UNA vez; las relecturas van por caché
($0.25/Mtok). Todo streamea (turnos de minutos) y loguea costo real.
"""
import asyncio
import inspect
import json
import os
import random
import subprocess
import sys
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "simcolombia"
load_dotenv(ROOT / ".env")

MODEL = os.environ.get("FABLE_MODEL", "claude-fable-5-1")
WS = os.environ.get("ANTHROPIC_WORKSPACE_ID", "").strip()
PRECIOS = {"in": 10.0, "out": 50.0, "cache_read": 0.25, "cache_write": 12.5}  # USD/Mtok

GASTO = {"in": 0, "out": 0, "cache_read": 0, "cache_write": 0}


def costo_usd():
    return sum(GASTO[k] * PRECIOS[k] / 1e6 for k in GASTO)


def marcador(usage):
    GASTO["in"] += getattr(usage, "input_tokens", 0) or 0
    GASTO["out"] += getattr(usage, "output_tokens", 0) or 0
    GASTO["cache_read"] += getattr(usage, "cache_read_input_tokens", 0) or 0
    GASTO["cache_write"] += getattr(usage, "cache_creation_input_tokens", 0) or 0
    print(f"\n💰 acumulado esta sesión: ${costo_usd():.3f} "
          f"(in {GASTO['in']:,} · out {GASTO['out']:,} · cache↓ {GASTO['cache_read']:,})")
    beam("fable_costo", {"usd": round(costo_usd(), 4), **GASTO})


def beam(evento, payload):
    """El visor del enjambre muestra a Fable trabajando en vivo."""
    try:
        req = urllib.request.Request(
            f"{os.environ['SUPABASE_URL']}/rest/v1/army_events",
            data=json.dumps({"run_id": "fable-showtime", "event": evento,
                             "payload": payload}).encode(),
            headers={"apikey": os.environ["SUPABASE_PUBLISHABLE_KEY"],
                     "Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=6)
    except Exception:
        pass


def cliente():
    if os.environ.get("FABLE_ENABLED", "0") != "1":
        sys.exit("🛑 FABLE_ENABLED=0 — cambia a 1 en .env cuando Daniel dé la orden.")
    from anthropic import AsyncAnthropic
    # timeout generoso (turnos de minutos) + reintentos del SDK para 429/529:
    # un reset a mitad de acto NO puede tumbar el show.
    return AsyncAnthropic(timeout=900.0, max_retries=2,
                          default_headers={"anthropic-workspace-id": WS} if WS else None)


async def fable(system_blocks, user, max_tokens=4000, effort=None, titulo=""):
    """Una llamada streameada a Fable con marcador de costo."""
    c = cliente()
    kwargs = dict(model=MODEL, max_tokens=max_tokens, system=system_blocks,
                  messages=[{"role": "user", "content": user}])
    if effort:
        kwargs["output_config"] = {"effort": effort}
    # soporte de output_config se detecta UNA vez, antes de streamear: nada de
    # retry ciego (re-ejecutar el stream paga dos veces el corpus cacheado).
    try:
        firma = inspect.signature(c.messages.stream).parameters
    except (TypeError, ValueError):
        firma = None
    if firma is not None:
        sobran = sorted(k for k in kwargs if k not in firma)
        if sobran:
            print(f"⚠️ SDK sin soporte para {', '.join(sobran)} → "
                  "degradado a default (sin retry)")
            kwargs = {k: v for k, v in kwargs.items() if k in firma}
    print(f"\n🧠 FABLE {('· ' + titulo) if titulo else ''} (streaming…)\n" + "─" * 60)
    beam("fable_inicio", {"acto": titulo})
    texto = []
    # max_retries del SDK solo cubre fallos ANTES del primer byte; un corte a
    # mitad de stream se reintenta aquí (1 vez) para que el acto no muera.
    for intento in range(2):
        try:
            async with c.messages.stream(**kwargs) as s:
                async for ev in s.text_stream:
                    print(ev, end="", flush=True)
                    texto.append(ev)
                final = await s.get_final_message()
            break
        except Exception as e:
            if intento == 1:
                raise
            print(f"\n⚠️ stream cortado ({type(e).__name__}) — reintento único…")
            texto = []
            await asyncio.sleep(3)
    print("\n" + "─" * 60)
    marcador(final.usage)
    if final.stop_reason == "refusal":
        print("⚠️ stop=refusal: reformula la pregunta (nota del system card).")
    return "".join(texto)


# ── PAÍS: serializar Colombia entera y cachearla ────────────────────────────
CORPUS = BASE / "data" / "eval" / "pais_corpus.txt"

VENTANA = int(os.environ.get("FABLE_CONTEXT", "1000000"))  # Fable 5.1: 1M de contexto
TOPE = 0.80  # margen de seguridad: nunca llegamos al 100% de la ventana


def contar_tokens(txt):
    """Tokens reales vía count_tokens; si no se puede, cota por bytes UTF-8
    (len//4 subestima con multibyte: ~3 bytes/token es más honesto)."""
    if os.environ.get("FABLE_ENABLED", "0") == "1":
        try:
            import anthropic
            c = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
            r = c.messages.count_tokens(model=MODEL,
                                        messages=[{"role": "user", "content": txt}])
            return r.input_tokens
        except Exception:
            pass
    return len(txt.encode("utf-8")) // 3


def cargar(path):
    return json.loads((ROOT / path).read_text())


def serializar_pais():
    res = cargar("dashboard/sim/residents.json")
    marg = cargar("dashboard/sim/marginals.json")["departamentos"]
    dos = cargar("dashboard/sim/dossiers.json")
    # tertulias reales de hoy desde Supabase
    try:
        req = urllib.request.Request(
            f"{os.environ['SUPABASE_URL']}/rest/v1/sim_encuestas?select=*&order=id.asc&limit=400",
            headers={"apikey": os.environ["SUPABASE_PUBLISHABLE_KEY"]})
        encu = json.load(urllib.request.urlopen(req, timeout=20))
    except Exception:
        encu = []
    partes = ["=== SIM COLOMBIA · CORPUS COMPLETO (fuentes DANE citadas) ===\n"]
    partes.append("\n== MARGINALES REALES POR TERRITORIO ==\n" +
                  json.dumps(marg, ensure_ascii=False))
    partes.append("\n== DOSSIERS Y VOCES REGIONALES ==\n" +
                  json.dumps(dos, ensure_ascii=False))
    partes.append("\n== LOS 6.600 RESIDENTES (uno por línea) ==\n" + "\n".join(
        f"{r['id']}|{r['nombre']}|{r['edad']}|{r['sexo']}|{r['dpto_nombre']}|"
        f"{r['ocupacion']}|{r.get('educacion','')}|{r['regimen_salud']}"
        for r in res))
    partes.append("\n== DELIBERACIONES DE HOY (guiones reales) ==\n" +
                  json.dumps(encu, ensure_ascii=False))
    txt = "\n".join(partes)
    CORPUS.parent.mkdir(parents=True, exist_ok=True)
    tok = contar_tokens(txt)
    if tok > VENTANA * TOPE:
        CORPUS.write_text(txt)  # se deja en disco solo para inspección
        sys.exit(
            f"🛑 corpus de {tok:,} tokens > {TOPE:.0%} del context window "
            f"({VENTANA:,}): la llamada fallaría DESPUÉS de pagar la subida. "
            f"Omite/comprime residentes o parte dossiers antes de volver a "
            f"correr, o sube FABLE_CONTEXT si la ventana es mayor. "
            f"Corpus sin usar en {CORPUS}")
    CORPUS.write_text(txt)
    print(f"📦 corpus: {len(txt):,} chars · {len(txt.encode('utf-8')):,} bytes "
          f"(~{tok:,} tokens) → {CORPUS}")
    print(f"   costo estimado 1ª lectura: ${tok*PRECIOS['in']/1e6:.2f} · "
          f"relecturas: ${tok*PRECIOS['cache_read']/1e6:.3f} · "
          f"uso {tok/VENTANA:.0%} de la ventana")


def system_pais():
    cuerpo = CORPUS.read_text()
    tok = contar_tokens(cuerpo)
    if tok > VENTANA * TOPE:
        i = cuerpo.find("== LOS 6.600 RESIDENTES")
        j = cuerpo.find("\n== ", i + 1) if i != -1 else -1
        if i != -1 and j != -1:
            cuerpo = cuerpo[:i] + "[…residentes omitidos por tamaño…]\n" + cuerpo[j:]
        tok2 = contar_tokens(cuerpo)
        if tok2 > VENTANA * TOPE:
            sys.exit(f"🛑 corpus de {tok2:,} tokens > {TOPE:.0%} de la ventana "
                     f"({VENTANA:,}) incluso sin residentes: particiona "
                     f"dossiers/encuestas antes de llamar a Fable.")
        print(f"⚠️ corpus de {tok:,} tokens: omito residentes, quedan {tok2:,}")
    return [
        {"type": "text",
         "text": "Eres el científico jefe examinando a Sim Colombia, un país "
                 "sintético construido de marginales DANE reales. Respondes con "
                 "evidencia citada del corpus (ids, celdas, números). Denso, "
                 "riguroso, en español. El corpus completo:\n\n" + cuerpo,
         "cache_control": {"type": "ephemeral"}},
    ]


CACHE_ACTOS = BASE / "fable" / "cache"


def grabar(slug, texto):
    """Cada acto queda grabado → 'replay <slug>' lo re-muestra gratis.
    Nombre con secuencia: varias preguntas de la sala NO se pisan entre sí."""
    try:
        CACHE_ACTOS.mkdir(parents=True, exist_ok=True)
        previos = [int(p.stem.rsplit("-", 1)[1]) for p in CACHE_ACTOS.glob(f"{slug}-*.txt")
                   if p.stem.rsplit("-", 1)[1].isdigit()]
        n = max(previos, default=0) + 1
        (CACHE_ACTOS / f"{slug}-{n:02d}.txt").write_text(texto)
    except Exception:
        pass


def replay(patron=""):
    import time
    grabados = sorted(CACHE_ACTOS.glob("*.txt")) if CACHE_ACTOS.exists() else []
    if not grabados:
        sys.exit("📼 nada grabado aún — replay se llena solo cuando corren los actos.")
    # slug exacto primero (que 'pais' no agarre 'pais_2050'), el MÁS RECIENTE
    exactos = [g for g in grabados if patron and g.stem.rsplit("-", 1)[0] == patron]
    hit = (max(exactos, key=lambda g: g.stat().st_mtime) if exactos else
           next((g for g in grabados if patron and patron in g.stem), None))
    if not hit:
        print("📼 grabados: " + ", ".join(g.stem for g in grabados))
        return
    print(f"\n📼 REPLAY · {hit.stem}\n" + "─" * 60)
    for linea in hit.read_text().splitlines():
        print(linea)
        time.sleep(0.02)  # ritmo de streaming, mismo teatro sin gastar un centavo
    print("─" * 60)


async def pais_ask(pregunta, slug="pais"):
    if not CORPUS.exists():
        serializar_pais()
    out = await fable(system_pais(), pregunta, max_tokens=3000, effort="high",
                      titulo="se leyó a Colombia entera")
    grabar(slug, f"PREGUNTA: {pregunta}\n\n{out}")


def prompt_2050():
    """Acto 3 sin pegar JSON a mano: arma el prompt desde marginals_2050.json."""
    m26 = cargar("dashboard/sim/marginals.json")["departamentos"]
    m50 = cargar("simcolombia/data/marginals_2050.json")["departamentos"]
    filas = []
    for cod in ("11", "05", "27", "88"):  # Bogotá, Antioquia, Chocó, San Andrés
        a, b = m26.get(cod, {}), m50.get(cod, {})
        if not (a.get("edad") and b.get("edad")):
            continue
        v26 = sum(v for g, v in a["edad"].items() if int(g.split("-")[0].rstrip("+")) >= 60)
        v50 = sum(v for g, v in b["edad"].items() if int(g.split("-")[0].rstrip("+")) >= 60)
        filas.append(f"- {a['nombre']}: 60+ pasa de {v26/max(a['poblacion'],1)*100:.1f}% "
                     f"(2026) a {v50/max(b['poblacion'],1)*100:.1f}% (2050); población "
                     f"{a['poblacion']:,} → {b['poblacion']:,}")
    return ("Compara la Colombia de hoy con la de 2050 según las proyecciones "
            "oficiales DANE (mismas fuentes del corpus). Celdas reales:\n" +
            "\n".join(filas) +
            "\n\n¿Qué opiniones de las tertulias de hoy crees que envejecen y "
            "cuáles resisten? Habla de EFECTO DE COMPOSICIÓN (las cohortes de hoy "
            "envejecidas), no de profecías. Cita residentes y celdas del corpus.")


# ── AUDITOR: encuesta estratificada vs verdad publicada ─────────────────────
async def auditor(n_por_celda=6):
    verdad = json.loads((BASE / "fable" / "verdad.json").read_text())
    res = [r for r in cargar("dashboard/sim/residents.json") if r["edad"] >= 18]
    rng = random.Random(2026)
    celdas = {}
    for r in res:
        edu = "superior" if r.get("educacion") == "superior" else "no_superior"
        eg = "joven" if r["edad"] < 35 else "adulto" if r["edad"] < 60 else "mayor"
        celdas.setdefault((r["sexo"], eg, edu), []).append(r)
    muestra = []
    for c, pool in sorted(celdas.items()):
        muestra += rng.sample(pool, min(n_por_celda, len(pool)))
    rng.shuffle(muestra)
    print(f"🎯 muestra estratificada: {len(muestra)} residentes × "
          f"{len(verdad['items'])} preguntas")
    preguntas = "\n".join(f"{i['id']}: {i['pregunta']} (responde: si|no)"
                          for i in verdad["items"])
    resultados = []
    LOTE = 6  # 6 personas × 10 ítems ≈ 1.400 tk de JSON: cabe holgado en el tope
    for i in range(0, len(muestra), LOTE):
        lote = muestra[i:i+LOTE]
        fichas = "\n".join(
            f"- {r['id']}: {r['nombre']}, {r['edad']}, {r['sexo']}, "
            f"{r['ocupacion']}, educación {r.get('educacion','?')}, "
            f"{r['dpto_nombre']}" for r in lote)
        out = await fable(
            [{"type": "text", "text":
              "Eres varios colombianos sintéticos a la vez. Para CADA persona listada, "
              "responde cada pregunta como respondería ESA persona (su edad, "
              "educación, territorio y vida mandan; sé fiel aunque la respuesta sea "
              "impopular). Devuelve SOLO JSON: {\"<id_persona>\":{\"<id_pregunta>\":\"si|no\"}}",
              "cache_control": {"type": "ephemeral"}}],
            f"PERSONAS:\n{fichas}\n\nPREGUNTAS:\n{preguntas}",
            max_tokens=min(400 + len(lote) * len(verdad["items"]) * 30, 4000),
            effort="medium", titulo=f"encuestando lote {i//LOTE+1}")
        try:
            import re
            m = re.search(r"\{.*\}", out, re.S)
            resultados.append(json.loads(m.group()))
        except Exception:
            print("⚠️ lote ilegible, sigo")
    (BASE / "data" / "eval" / "auditor_respuestas.json").write_text(
        json.dumps(resultados, ensure_ascii=False))
    # agregado simple + venia el informe
    agg = {i["id"]: {"si": 0, "no": 0} for i in verdad["items"]}
    for lote in resultados:
        if not isinstance(lote, dict):
            continue
        for rid, resp in lote.items():
            if not isinstance(resp, dict):
                continue
            for qid, v in resp.items():
                if qid in agg and str(v).lower() in ("si", "sí", "no"):
                    agg[qid]["si" if str(v).lower().startswith("s") else "no"] += 1
    print("\n📊 SINTÉTICO vs REAL:")
    lineas = []
    for it in verdad["items"]:
        a = agg[it["id"]]
        tot = a["si"] + a["no"] or 1
        sint = a["si"] / tot * 100
        lineas.append(f"{it['id']}: sintético {sint:.0f}% vs real "
                      f"{it['valor_real_pct']}% ({it['fuente']})")
        print("  " + lineas[-1])
    await fable(
        [{"type": "text", "text": "Eres el sociólogo auditor. Español, denso, con números."}],
        "Escribe el veredicto del sesgo de Sim Colombia (máx 400 palabras): qué "
        "sobre/subestima y la hipótesis del porqué (sesgos LLM documentados: "
        "deseabilidad social, WEIRD, aplanamiento). Datos:\n" + "\n".join(lineas),
        max_tokens=1200, effort="max", titulo="veredicto del auditor")


# ── FORENSE: las tertulias de hoy bajo el microscopio ───────────────────────
async def forense():
    if not CORPUS.exists():
        serializar_pais()
    await fable(system_pais(),
        "FORENSE DE DELIBERACIONES. Sobre los guiones de '== DELIBERACIONES DE "
        "HOY ==': (1) ¿los cambios de postura vienen de argumentos o de "
        "complacencia? cita 3 casos con nombre y turno; (2) ¿convergen más "
        "rápido que grupos humanos reales (America in One Room: actualización "
        "modesta y asimétrica)?; (3) detecta anclaje (Hidden Anchors) y "
        "plantillas repetidas; (4) nota 0-10 de realismo deliberativo con "
        "desglose. Máx 500 palabras, con evidencia.",
        max_tokens=2000, effort="max", titulo="forense de deliberaciones")


# ── DUELO CIEGO: enjambre vs Fable, juez ciego ──────────────────────────────
RETOS = [
 ("facil_resumen", "Resume en exactamente 3 frases por qué el café colombiano subió de precio en 2025-2026."),
 ("facil_carta", "Escribe una carta de 120-150 palabras de una junta de acción comunal pidiendo un parque a la alcaldía."),
 ("facil_tabla", "Tabla markdown de 5 filas: departamento colombiano, capital, plato típico, festival famoso."),
 ("duro_mate", "Tres amigos aportan $2.400.000 en razón 3:4:5 para un negocio que rinde 18% el primer año y pierde 10% el segundo. ¿Cuánto recibe cada uno si liquidan al final del año 2, y cuál es la TIR aproximada del que más aportó? Muestra el razonamiento."),
 ("duro_logica", "En una tertulia de 8 personas, cada una miente los martes y jueves y dice verdad el resto. Ana dice 'ayer mentí' y Beto dice 'mañana miento'. Si hoy no es fin de semana, ¿qué día es? Justifica."),
 ("duro_sintesis", "Un alcalde tiene $10.000 millones y tres opciones con estos datos: ciclorrutas (costo 100%/beneficio anual 12%, gini -0.001), buses eléctricos (100%/9%, gini -0.003), subsidio tarifa (100%/15% solo año 1, gini -0.005). Recomienda la cartera óptima si pondera equidad 2:1 sobre eficiencia, y di qué dato adicional pedirías primero."),
]


async def duelo():
    import re
    print("⚔️ EL DUELO CIEGO: enjambre 8×flash+Jev vs Fable 5.1 solo\n")
    # lado A: enjambre (plan de 6 tareas)
    plan = {"task": "Duelo ciego del Build Day: seis retos directos.",
            "tasks": [{"id": rid, "thinking": "high" if rid.startswith("duro") else "none",
                       "filename": f"{rid}.md", "prompt": p} for rid, p in RETOS]}
    pf = ROOT / "orchestrator" / "plans" / "duelo.json"
    pf.write_text(json.dumps(plan, ensure_ascii=False))
    print("🐝 enjambre trabajando…")
    t_antes = __import__("time").time()
    sw = subprocess.run([sys.executable, str(ROOT / "orchestrator" / "swarm.py"),
                         "--plan", str(pf)], cwd=ROOT)
    candidatos = [p for p in (ROOT / "runs").glob("*-swarm")
                  if p.stat().st_mtime >= t_antes - 5]
    if sw.returncode != 0 or not candidatos:
        sys.exit("🛑 el enjambre falló o no dejó run fresco — el duelo necesita "
                 "las dos esquinas. Revisa orchestrator y reintenta.")
    run = max(candidatos, key=lambda p: p.stat().st_mtime)
    lado_a = {rid: (run / "artifacts" / f"{rid}.md").read_text()
              for rid, _ in RETOS if (run / "artifacts" / f"{rid}.md").exists()}
    # lado B: Fable solo
    lado_b = {}
    for rid, p in RETOS:
        lado_b[rid] = await fable(
            [{"type": "text", "text": "Responde directo y completo. Español."}],
            p, max_tokens=900, effort="high" if rid.startswith("duro") else "low",
            titulo=f"duelo · {rid}")
    # juez ciego: Jev, orden aleatorio, longitud normalizada
    rng = random.Random()
    marcador_txt = []
    puntos = {"enjambre": 0, "fable": 0}
    for rid, p in RETOS:
        a, b = lado_a.get(rid, "").strip(), lado_b.get(rid, "").strip()
        if not a or not b:
            marcador_txt.append(f"{rid}: ⚠️ sin respuesta de un lado — anulado")
            print("  " + marcador_txt[-1])
            continue
        n = min(len(a), len(b), 1800)
        par = [("enjambre", a[:n]), ("fable", b[:n])]
        rng.shuffle(par)
        state = (f"RETO: {p}\n\nRESPUESTA 1:\n{par[0][1]}\n\nRESPUESTA 2:\n{par[1][1]}")
        req = urllib.request.Request(
            "https://openrouter.ai/api/alpha/decisions",
            data=json.dumps({"model": "typesafe/jev-1.13", "state": state,
                "questions": {"mejor": {"type": "choice",
                    "instructions": "La respuesta que mejor resuelve el reto (corrección primero, claridad después; ignora cuál es más larga)",
                    "criteria": {"respuesta_1": "la primera es mejor",
                                 "respuesta_2": "la segunda es mejor"}}}}).encode(),
            headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
                     "Content-Type": "application/json"})
        ganador = "empate"
        for intento in range(2):
            try:
                j = json.load(urllib.request.urlopen(req, timeout=30))
                eleccion = j.get("answers", {}).get("mejor", {}).get("choice")
                if eleccion in ("respuesta_1", "respuesta_2"):
                    ganador = par[0][0] if eleccion == "respuesta_1" else par[1][0]
                else:
                    print(f"  ⚠️ juez devolvió {eleccion!r} — empate técnico")
                break
            except Exception:
                if intento == 0:
                    continue  # un reintento y ya: el show no se detiene por el juez
        if ganador in puntos:
            puntos[ganador] += 1
        marcador_txt.append(f"{rid}: 🏆 {ganador}")
        print(f"  {marcador_txt[-1]}")
    print(f"\n⚔️ MARCADOR FINAL: enjambre {puntos['enjambre']} — "
          f"{puntos['fable']} fable · predicción de los papers: enjambre gana lo "
          f"fácil, Fable lo duro. Compárenlo fila a fila.")
    beam("fable_duelo", {"marcador": puntos, "detalle": marcador_txt})


# ── COLOMBIA 2050 ────────────────────────────────────────────────────────────
def d2050():
    env = {**os.environ, "AÑO_SIM": "2050", "SIM_SUFIJO": "_2050"}
    for script in ("build_marginals.py", "generate_population.py"):
        subprocess.run([sys.executable, str(BASE / "pipeline" / script)],
                       env=env, cwd=ROOT, check=True)
    print("🕰 Colombia 2050 generada → dashboard/sim/residents_2050.json")
    print("   compárala: mismas preguntas a las dos Colombias y Fable analiza "
          "el corrimiento (pais ask con ambos archivos, o sondeos gemelos).")


async def ping():
    out = await fable([{"type": "text", "text": "Responde en 5 palabras."}],
                      "¿Listo para el Build Day?", max_tokens=30, titulo="ping")
    print(f"\n✅ Fable vivo: {out.strip()!r}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "ping"
    if cmd == "pais" and sys.argv[2:] == ["serialize"]:
        serializar_pais()
    elif cmd == "pais" and sys.argv[2:] == ["2050"]:
        asyncio.run(pais_ask(prompt_2050(), slug="pais_2050"))
    elif cmd == "pais":
        asyncio.run(pais_ask(" ".join(sys.argv[2:]) or "Preséntate y di qué ves."))
    elif cmd == "preguntar":
        # preguntas del público SIN pelear con el shell: se escriben aquí
        while True:
            try:
                q = input("\n🎤 pregunta de la sala (vacío = salir): ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not q:
                break
            asyncio.run(pais_ask(q, slug="sala"))
    elif cmd == "replay":
        replay(" ".join(sys.argv[2:]))
    elif cmd == "auditor":
        asyncio.run(auditor())
    elif cmd == "forense":
        asyncio.run(forense())
    elif cmd == "duelo":
        asyncio.run(duelo())
    elif cmd == "d2050":
        d2050()
    else:
        asyncio.run(ping())
