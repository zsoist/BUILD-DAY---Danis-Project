#!/usr/bin/env python3
"""Fable 5.1 orquesta hasta 8 agentes DeepSeek en paralelo.

Uso:
    uv run --project orchestrator python orchestrator/fable_orchestrator.py "tu reto"

Flujo por ronda: PLAN (Fable) -> EXECUTE (DeepSeek x8, OpenRouter fallback)
-> SYNTHESIZE (Fable decide DONE o CONTINUE, max 3 rondas).
"""

import asyncio
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

from anthropic import AsyncAnthropic
from dotenv import load_dotenv
from openai import AsyncOpenAI

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

FABLE_MODEL = os.environ.get("FABLE_MODEL", "claude-fable-5-1")
MAX_AGENTS = int(os.environ.get("MAX_DEEPSEEK_AGENTS", "8"))
MAX_ROUNDS = 3
WORKER_SUMMARY_CHARS = 1500  # lo máximo que un worker aporta al contexto de Fable

RUNS_DIR = ROOT / "runs"
RUNS_DIR.mkdir(exist_ok=True)

# La key del evento no está scoped a un workspace: la API exige el header
# anthropic-workspace-id (ANTHROPIC_WORKSPACE_ID en .env).
_ws = os.environ.get("ANTHROPIC_WORKSPACE_ID", "").strip()
fable = AsyncAnthropic(  # ANTHROPIC_API_KEY del entorno
    default_headers={"anthropic-workspace-id": _ws} if _ws else None
)
deepseek = AsyncOpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
)
openrouter = AsyncOpenAI(
    api_key=os.environ["OPENROUTER_API_KEY"],
    base_url=os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
)

# cache_control en el primer bloque del system: se reusa entre PLAN y SYNTHESIZE
# de todas las rondas, así el costo de contexto de Fable se paga una sola vez.
FABLE_SYSTEM = [
    {
        "type": "text",
        "text": (
            "Eres Fable 5.1 orquestando un enjambre de hasta "
            f"{MAX_AGENTS} agentes DeepSeek durante el Build Day de Bogotá. "
            "Descompones problemas difíciles en subtareas paralelas e "
            "independientes, y sintetizas los resultados. Sé quirúrgico con "
            "los tokens: subtareas autocontenidas, sin redundancia entre "
            "agentes, cada una con criterio de éxito claro.\n\n"
            "Cuando se te pida un PLAN respondes SOLO un JSON:\n"
            '{"subtasks": [{"id": "t1", "model": "deepseek-flash" | '
            '"deepseek-v4-pro", "prompt": "..."}]}\n'
            f"(máx {MAX_AGENTS} subtareas; usa deepseek-v4-pro solo para "
            "razonamiento pesado: matemáticas, pruebas, algoritmos).\n\n"
            "Cuando se te pida SYNTHESIZE respondes SOLO un JSON:\n"
            '{"verdict": "DONE" | "CONTINUE", "synthesis": "...", '
            '"next_focus": "..." }'
        ),
        "cache_control": {"type": "ephemeral"},
    }
]


def extract_json(text: str) -> dict:
    """Toma el primer objeto JSON del texto (tolera fences de markdown)."""
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"Fable no devolvió JSON:\n{text[:500]}")
    return json.loads(match.group())


FABLE_ENABLED = os.environ.get("FABLE_ENABLED", "0") == "1"


async def ask_fable(prompt: str, max_tokens: int = 4000) -> str:
    if not FABLE_ENABLED:
        sys.exit(
            "💰 Fable via API está DESACTIVADO (FABLE_ENABLED=0 en .env). "
            "Es caro: actívalo solo con autorización explícita de Daniel. "
            "Para probar el enjambre sin Fable: --test-workers"
        )
    resp = await fable.messages.create(
        model=FABLE_MODEL,
        max_tokens=max_tokens,
        system=FABLE_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text


async def run_worker(sem: asyncio.Semaphore, sub: dict, log) -> dict:
    """Un agente DeepSeek. API nativa primero, OpenRouter como fallback."""
    model = sub.get("model", "deepseek-flash")
    messages = [{"role": "user", "content": sub["prompt"]}]
    async with sem:
        t0 = time.monotonic()
        try:
            resp = await deepseek.chat.completions.create(
                model=model, messages=messages, timeout=300
            )
            via = "deepseek"
        except Exception as e:
            print(f"  ⚠️  {sub['id']} falló en DeepSeek ({e}); reintento vía OpenRouter")
            resp = await openrouter.chat.completions.create(
                model="deepseek/deepseek-v4.1-flash", messages=messages, timeout=300
            )
            via = "openrouter"
        output = resp.choices[0].message.content or ""
        elapsed = time.monotonic() - t0
    log({"event": "worker_done", "id": sub["id"], "via": via,
         "seconds": round(elapsed, 1), "output": output})
    print(f"  ✅ {sub['id']} listo ({via}, {elapsed:.0f}s, {len(output)} chars)")
    return {"id": sub["id"], "summary": output[:WORKER_SUMMARY_CHARS]}


async def main(task: str):
    run_file = RUNS_DIR / f"{datetime.now():%Y%m%d-%H%M%S}.jsonl"
    def log(obj):
        with run_file.open("a") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    log({"event": "start", "task": task, "fable": FABLE_MODEL})
    sem = asyncio.Semaphore(MAX_AGENTS)
    focus = task

    for round_n in range(1, MAX_ROUNDS + 1):
        print(f"\n🧠 Ronda {round_n} — Fable planifica…")
        plan = extract_json(await ask_fable(
            f"PLAN. Reto:\n{task}\n\nEnfoque de esta ronda:\n{focus}"
        ))
        subtasks = plan["subtasks"][:MAX_AGENTS]
        log({"event": "plan", "round": round_n, "subtasks": subtasks})
        print(f"🚀 Despachando {len(subtasks)} agentes DeepSeek en paralelo…")

        results = await asyncio.gather(
            *(run_worker(sem, s, log) for s in subtasks)
        )

        print("🧠 Fable sintetiza…")
        verdict = extract_json(await ask_fable(
            "SYNTHESIZE. Reto original:\n" + task
            + "\n\nResultados de los agentes:\n"
            + json.dumps(results, ensure_ascii=False),
            max_tokens=8000,
        ))
        log({"event": "synthesis", "round": round_n, **verdict})
        print(f"\n📋 Síntesis (ronda {round_n}):\n{verdict['synthesis']}\n")

        if verdict.get("verdict") == "DONE":
            break
        focus = verdict.get("next_focus", focus)
        print(f"🔁 Continuando. Nuevo enfoque: {focus}")

    print(f"📁 Log completo: {run_file}")


async def test_workers(n: int):
    """Prueba el enjambre DeepSeek/OpenRouter en paralelo SIN tocar Fable ($0 Anthropic)."""
    run_file = RUNS_DIR / f"{datetime.now():%Y%m%d-%H%M%S}-workertest.jsonl"
    def log(obj):
        with run_file.open("a") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    sem = asyncio.Semaphore(MAX_AGENTS)
    subs = [
        {"id": f"w{i+1}", "model": "deepseek-flash",
         "prompt": f"Eres el agente {i+1} de un enjambre de {n}. "
                   f"Responde en UNA línea: tu número y la palabra LISTO."}
        for i in range(n)
    ]
    print(f"🧪 Probando {n} workers en paralelo (sin Fable)…")
    t0 = time.monotonic()
    results = await asyncio.gather(*(run_worker(sem, s, log) for s in subs))
    print(f"\n✅ {len(results)}/{n} workers respondieron en {time.monotonic()-t0:.0f}s total")
    print(f"📁 Log: {run_file}")


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "--test-workers":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else MAX_AGENTS
        asyncio.run(test_workers(n))
    elif len(sys.argv) >= 2:
        asyncio.run(main(" ".join(sys.argv[1:])))
    else:
        sys.exit('Uso: fable_orchestrator.py "reto"  |  --test-workers [n]')
