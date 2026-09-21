# Fable 5.1 Build Day — Bogotá (2026-09-21)

Workspace para el Build Day (Universidad de La Sabana, 6-9 PM). Máquina dedicada:
MacBook Air M4, 16 GB — esta carpeta es LO ÚNICO que corre hoy.

## Arquitectura del proyecto

**Fable 5.1 orquesta, DeepSeek ejecuta.** Fable (`claude-fable-5-1`) es el cerebro:
descompone el problema, despacha subtareas a hasta 8 agentes DeepSeek en paralelo,
sintetiza resultados. OpenRouter es fallback y fuente de modelos extra.

Harness principal: **`orchestrator/swarm.py`** — pipeline ship-first (DAG + worker
pool, sin barreras, gate heurístico por tarea, budget con auto-stop). Ver
`orchestrator/CLAUDE.md` para el detalle.

```
Planner (Fable si autorizado; hoy deepseek-v4-pro)
 └─ DAG de tareas → worker pool (≤8 deepseek-flash, fallback OpenRouter)
     ├─ cada output se shippea a disco al instante (runs/<ts>-swarm/artifacts/)
     ├─ gate barato por tarea; 1 intento de fix; sin re-verificación global
     └─ Assembler (Fable/reasoner) ensambla FINAL.md
```

## 💰 Política de costos (REGLA DURA)

- **Fable via API SOLO con autorización explícita de Daniel.** `FABLE_ENABLED=0`
  en `.env` lo mantiene apagado; el orquestador se niega a llamar a Anthropic si no está en 1.
- La key de Anthropic además necesita `ANTHROPIC_WORKSPACE_ID` (Daniel la da el día del evento).
- Para probar el enjambre gratis (solo DeepSeek/OpenRouter, costo ~nada):
  `uv run --project orchestrator python orchestrator/fable_orchestrator.py --test-workers 8`
- La calibración/preparación previa la hace Claude Code (esta sesión), no la API de Fable.

**Presupuestos de hoy (2026-09-21, fijados por Daniel):**
| Proveedor | Techo | Uso |
|---|---|---|
| DeepSeek | USD $10 | libre para pruebas/calibración hoy |
| OpenRouter | USD $10 | libre para pruebas/calibración hoy |
| Anthropic (Fable) | USD $100 | SOLO en el evento, con autorización explícita |

## Reglas de eficiencia de tokens

- Fable recibe **resúmenes** de los workers, nunca transcripts completos.
- System prompt de Fable con `cache_control` (prompt caching) — se reusa entre rondas.
- Workers DeepSeek: prompts autocontenidos, sin historial acumulado entre subtareas.
- Concurrencia con `asyncio.gather`, semáforo en `MAX_DEEPSEEK_AGENTS` (=8).
- Cada corrida escribe su log en `runs/` (gitignoreado) — Fable puede releer solo lo necesario.

## Convenciones

- Python 3.14 + `uv` (deps en `orchestrator/pyproject.toml`).
- Credenciales SOLO en `.env` (raíz). Nunca en código ni en commits.
- Correr todo desde la raíz: `uv run --project orchestrator python orchestrator/fable_orchestrator.py "tarea"`.
- Verificar APIs antes de empezar: `./scripts/check_apis.sh`.

## Modelos (jerarquía militar — exprimir los $100)

| Rango | Rol | Modelo | Vía |
|---|---|---|---|
| General | plan inicial, decisiones de máxima palanca (SOLO cuando hace falta) | `claude-fable-5-1` | Anthropic API |
| Oficial | ensamblajes, decisiones intermedias | `claude-opus-5` | Anthropic API |
| Tropa (x8) | ejecución, thinking graduado por tarea | `deepseek-flash` | api.deepseek.com |
| Cerebro suplente (hoy) | planner/assembler mientras Fable está apagado | `deepseek-v4-pro` | api.deepseek.com |
| Juez/gate | aprueba cada output (~$0.00002/llamada) | `typesafe/jev-1.13` | OpenRouter /decisions |
| Fallback tropa | si DeepSeek nativo falla | `deepseek/deepseek-v4.1-flash` | OpenRouter |

## Cuenta / créditos

- platform.claude.com: cuenta del evento (email en `.env`, nunca en el repo) — los USD $100 se aplican al **Org ID**, no a la cuenta personal de claude.ai. Confirmar Org creada antes de las 6 PM.
