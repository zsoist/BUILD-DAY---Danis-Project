#!/usr/bin/env python3
"""SHOWTIME — el gatillo de los $100. Fable 5.1 sobre Sim Colombia.

Todo precableado: la noche del evento solo se corre esto.

  uv run --project orchestrator python simcolombia/fable/showtime.py ping
  ...                                                          pais serialize
  ...                                                          pais ask "¿pregunta?"
  ...                                                          auditor
  ...                                                          forense
  ...                                                          duelo
  ...                                                          d2050

Requisitos: FABLE_ENABLED=1 en .env (la key y el workspace ya están).
Economía: corpus del país se paga UNA vez; las relecturas van por caché
($0.25/Mtok). Todo streamea (turnos de minutos) y loguea costo real.
"""
import asyncio
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
    return AsyncAnthropic(default_headers={"anthropic-workspace-id": WS} if WS else None)


async def fable(system_blocks, user, max_tokens=4000, effort=None, titulo=""):
    """Una llamada streameada a Fable con marcador de costo."""
    c = cliente()
    kwargs = dict(model=MODEL, max_tokens=max_tokens, system=system_blocks,
                  messages=[{"role": "user", "content": user}])
    if effort:
        kwargs["output_config"] = {"effort": effort}
    print(f"\n🧠 FABLE {('· ' + titulo) if titulo else ''} (streaming…)\n" + "─" * 60)
    beam("fable_inicio", {"acto": titulo})
    texto = []
    try:
        async with c.messages.stream(**kwargs) as s:
            async for ev in s.text_stream:
                print(ev, end="", flush=True)
                texto.append(ev)
            final = await s.get_final_message()
    except TypeError:
        # SDK sin output_config: reintento sin effort
        kwargs.pop("output_config", None)
        async with c.messages.stream(**kwargs) as s:
            async for ev in s.text_stream:
                print(ev, end="", flush=True)
                texto.append(ev)
            final = await s.get_final_message()
    print("\n" + "─" * 60)
    marcador(final.usage)
    if final.stop_reason == "refusal":
        print("⚠️ stop=refusal: reformula la pregunta (nota del system card).")
    return "".join(texto)


# ── PAÍS: serializar Colombia entera y cachearla ────────────────────────────
CORPUS = BASE / "data" / "eval" / "pais_corpus.txt"


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
    CORPUS.write_text(txt)
    print(f"📦 corpus: {len(txt):,} chars (~{len(txt)//4:,} tokens) → {CORPUS}")
    print(f"   costo estimado 1ª lectura: ${len(txt)/4*PRECIOS['in']/1e6:.2f} · "
          f"relecturas: ${len(txt)/4*PRECIOS['cache_read']/1e6:.3f}")


def system_pais():
    return [
        {"type": "text",
         "text": "Eres el científico jefe examinando a Sim Colombia, un país "
                 "sintético construido de marginales DANE reales. Respondes con "
                 "evidencia citada del corpus (ids, celdas, números). Denso, "
                 "riguroso, en español. El corpus completo:\n\n" +
                 CORPUS.read_text(),
         "cache_control": {"type": "ephemeral"}},
    ]


async def pais_ask(pregunta):
    if not CORPUS.exists():
        serializar_pais()
    await fable(system_pais(), pregunta, max_tokens=3000, effort="high",
                titulo="se leyó a Colombia entera")


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
    LOTE = 10
    for i in range(0, len(muestra), LOTE):
        lote = muestra[i:i+LOTE]
        fichas = "\n".join(
            f"- {r['id']}: {r['nombre']}, {r['edad']}, {r['sexo']}, "
            f"{r['ocupacion']}, educación {r.get('educacion','?')}, "
            f"{r['dpto_nombre']}" for r in lote)
        out = await fable(
            [{"type": "text", "text":
              "Eres 10 colombianos sintéticos a la vez. Para CADA persona listada, "
              "responde cada pregunta como respondería ESA persona (su edad, "
              "educación, territorio y vida mandan; sé fiel aunque la respuesta sea "
              "impopular). Devuelve SOLO JSON: {\"<id_persona>\":{\"<id_pregunta>\":\"si|no\"}}",
              "cache_control": {"type": "ephemeral"}}],
            f"PERSONAS:\n{fichas}\n\nPREGUNTAS:\n{preguntas}",
            max_tokens=1500, effort="medium", titulo=f"encuestando lote {i//LOTE+1}")
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
        for rid, resp in lote.items():
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
    subprocess.run([sys.executable, str(ROOT / "orchestrator" / "swarm.py"),
                    "--plan", str(pf)], cwd=ROOT)
    run = sorted((ROOT / "runs").glob("*-swarm"))[-1]
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
        a, b = lado_a.get(rid, ""), lado_b.get(rid, "")
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
        try:
            j = json.load(urllib.request.urlopen(req, timeout=30))
            eleccion = j["answers"]["mejor"]["choice"]
            ganador = par[0][0] if eleccion == "respuesta_1" else par[1][0]
        except Exception as e:
            ganador = "empate"
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
    elif cmd == "pais":
        asyncio.run(pais_ask(" ".join(sys.argv[2:]) or "Preséntate y di qué ves."))
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
