# Fable 5.1 Build Day — Bogotá 🇨🇴

**Lunes 21 sep 2026, 6:00–9:00 PM** · Universidad de La Sabana, Chía
Aula Nexus, piso 0, Edificio Ad Portas (Campus Puente del Común, Km 7 Autopista Norte)
Hosts: Gabriel Alzate, Francisco Camacho (Claude Community Events)

## Agenda del evento

1. Novedades de Fable 5.1 (video + 2 demos en vivo, ~30 min)
2. Bloque de construcción (solo o equipos de 2–4, con helpers)
3. Demos de 2 minutos por equipo
4. Feedback directo a los equipos de producto/modelo de Anthropic

## Checklist pre-evento

- [x] Carpeta de trabajo preparada (esta)
- [x] Keys configuradas en `.env` (Anthropic, DeepSeek, OpenRouter)
- [ ] Verificar las 3 APIs: `./scripts/check_apis.sh`
- [ ] Confirmar Organización creada en platform.claude.com (créditos → Org ID)
- [ ] Laptop cargada + cargador
- [ ] Reto definido con contexto/código/datos listos (ver `ideas/PROJECT-IDEAS.md`)

## Estructura

```
CLAUDE.md               ← doctrina de orquestación (Fable la lee)
.env                    ← keys (NO commitear; rotar post-evento)
orchestrator/           ← Fable orquesta hasta 8 agentes DeepSeek
  fable_orchestrator.py
scripts/check_apis.sh   ← smoke test de las 3 APIs
ideas/PROJECT-IDEAS.md  ← candidatos de reto para el build day
runs/                   ← logs de cada corrida (gitignoreado)
```

## Uso rápido

```bash
./scripts/check_apis.sh
```

```bash
# Harness principal (v2 ship-first; hoy 100% DeepSeek, Fable solo con FABLE_ENABLED=1)
uv run --project orchestrator python orchestrator/swarm.py "tu reto aquí"
```

```bash
# Prueba del enjambre sin gastar nada de Anthropic
uv run --project orchestrator python orchestrator/fable_orchestrator.py --test-workers 8
```

## Post-evento

- [ ] Rotar las 3 API keys (quedaron expuestas en chat durante el setup)
