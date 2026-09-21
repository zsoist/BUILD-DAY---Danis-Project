# orchestrator/

Dos harnesses:

- **`swarm.py` (v2, EL PRINCIPAL)** — pipeline autónomo ship-first. DAG de tareas +
  worker pool deepseek-flash: cada tarea se despacha apenas sus deps resuelven, cada
  output se shippea a disco al instante (`runs/<ts>-swarm/artifacts/`), un solo
  intento de fix si falla el gate — NUNCA loops de re-verificación global. Planner y
  assembler: deepseek-v4-pro hoy, Fable cuando `FABLE_ENABLED=1`. Presupuesto con
  auto-stop (`Budget`, techos en `.env`). Checkpoint/resume: `--resume runs/<dir>`.
  Optimizaciones frontier ya cableadas:
  - **Thinking por tarea**: flash trae razonamiento ON por defecto ($$); el planner
    asigna `thinking: none|low|medium|high` y el harness lo apaga/gradúa por tarea
    (`thinking: disabled` / `reasoning_effort`). Temp 0.3 sin thinking, 0.6 con.
  - **Gate Jev**: `typesafe/jev-1.13` (OpenRouter `/api/alpha/decisions`) juzga cada
    output — noul calibrado, tipado, ~$0.00002/llamada, sin parsing. Si Jev no
    responde, cae al gate heurístico local.
  - **Constitución cacheada**: system prompt idéntico en todos los workers → el
    context caching automático de DeepSeek cobra el prefijo a ~2% después del 1er hit.
  - **Modelos verificados 2026-09-21**: nativos `deepseek-flash`/`deepseek-v4-pro`
    (los alias deepseek-chat/reasoner fueron RETIRADOS en julio 2026); OpenRouter
    `deepseek/deepseek-v4.1-flash` / `deepseek/deepseek-v4-pro`.
- **`fable_orchestrator.py` (v1)** — rondas lockstep plan→execute→synthesize.
  Se mantiene como referencia/comparación para la demo.

Filosofía (pedida por Daniel): shipping constante, no handover constante; autonomía
sobre verificación; velocidad de DeepSeek para el trabajo, inteligencia de Fable
solo en plan y ensamblaje.

## Flujo por ronda

1. **PLAN** — Fable descompone el reto en ≤8 subtareas JSON (`{"id", "prompt", "model"}`).
2. **EXECUTE** — workers DeepSeek corren en paralelo (asyncio + semáforo de 8).
   Cada worker: API nativa DeepSeek; si falla → retry vía OpenRouter (`deepseek/deepseek-flash`).
3. **SYNTHESIZE** — Fable recibe resúmenes (≤1500 chars c/u), produce síntesis y decide
   `CONTINUE` (nueva ronda, máx 3) o `DONE`.

## Reglas al editar

- El system prompt de Fable lleva `cache_control: {"type": "ephemeral"}` — no lo muevas
  del primer bloque del system, o se pierde el caching entre rondas.
- Workers no acumulan historial: cada subtarea es un mensaje autocontenido.
- Todo output crudo va a `runs/<timestamp>.jsonl`; a Fable solo le llegan resúmenes.
- No agregar dependencias sin necesidad — el loop es asyncio puro + 2 SDKs.
