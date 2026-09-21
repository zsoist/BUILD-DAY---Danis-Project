# GUION DEL EVENTO — todo listo, un solo paso pendiente

## EL ÚNICO PASO (cuando te den los $100)

Los créditos se aplican al Org ID — si llegan a TU org, la key actual ya los
usa. Si te dan una key nueva: pega en `.env` la línea `ANTHROPIC_API_KEY=` y:

```bash
sed -i '' 's/FABLE_ENABLED=0/FABLE_ENABLED=1/' .env
```

```bash
uv run --project orchestrator python simcolombia/fable/showtime.py ping
```

Si el ping contesta: estamos en el aire. TODO lo demás ya está precableado.

## LAS DOS PANTALLAS

- Proyector: https://build-day-danis-project.vercel.app/sim (y `/` para el visor
  del enjambre — los actos de Fable aparecen ahí en vivo con su gasto).
- Terminal local: los comandos de abajo (streaming en vivo — Fable piensa en
  minutos, deja que el público lo VEA pensar).

## EL PROGRAMA (comandos exactos, en orden)

```bash
uv run --project orchestrator python simcolombia/fable/showtime.py pais serialize
```

**ACTO 0 · "Se leyó a Colombia entera"** (~$2 la primera vez, 5¢ después):
```bash
uv run --project orchestrator python simcolombia/fable/showtime.py pais "Te acabas de leer un país entero: 6.600 personas, 33 territorios, todas sus deliberaciones de hoy. Preséntate y di tres cosas que viste que nosotros no."
```
Luego pregunta libre del público: `... pais "lo que grite la sala"`.

**ACTO 5 · El duelo ciego** (mueve al público temprano):
```bash
uv run --project orchestrator python simcolombia/fable/showtime.py duelo
```
Mientras corre: voto a mano alzada por reto (las respuestas van saliendo).

**ACTO 1 · El auditor** (necesita `simcolombia/fable/verdad.json` — ya viene
con los números publicados y sus fuentes):
```bash
uv run --project orchestrator python simcolombia/fable/showtime.py auditor
```

**ACTO 2 · El forense** (relee el caché → centavos):
```bash
uv run --project orchestrator python simcolombia/fable/showtime.py forense
```

**ACTO 3 · Colombia 2050** (la población YA está generada:
`dashboard/sim/residents_2050.json`):
```bash
uv run --project orchestrator python simcolombia/fable/showtime.py pais "Compara la pirámide de residents.json (2026) con la Colombia envejecida de 2050 que te describo: [pega 3-4 celdas de marginals_2050]. ¿Qué opiniones de las tertulias de hoy crees que envejecen y cuáles resisten? Efecto de composición, no profecía."
```

**ACTO 4 · El director de orquesta** (Fable al mando del enjambre, visor
proyectado):
```bash
uv run --project orchestrator python orchestrator/swarm.py "Analiza las 3 conclusiones más divididas del modo país de hoy y propone la pregunta que reconciliaría a los territorios"
```

## ADVERTENCIAS PARA DECIR EN ESCENA (rigor = puntos)
- 2050 es efecto de composición (cohortes envejecidas), no valores futuros.
- Varianza sintética artificialmente baja (Bisbee): corrimientos, no verdades.
- El duelo va ciego, aleatorizado y con longitud controlada (Zheng/MT-Bench).

## SI ALGO SE CAE
- Web caída → todo corre local: `python3 -m http.server 8377 --directory dashboard`.
- Fable lento → es normal (minutos); el streaming ES el espectáculo.
- `stop_reason: refusal` → reformular en una frase; sigue el show.
- Presupuesto en pantalla: cada acto imprime `💰 acumulado`.

## LA FRASE DE CIERRE
"Esta mañana no existía nada de esto. Un ejército de agentes de $0.15/M
construyó un país con el censo real. Esta noche, Fable 5.1 se lo leyó ENTERO
de una sentada, nos dijo dónde miente, cómo delibera mal, y qué opinará cuando
envejezca. Eso es hasta dónde llega el modelo."
