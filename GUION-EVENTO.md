# GUION DEL EVENTO — todo listo, un solo paso pendiente

Presupuesto estimado del show completo: ~$85 de los $100 (queda ~$15 de colchón).
Cada acto imprime `💰 acumulado` — si un acto se dispara, el siguiente se salta o
se hace por `replay`.

## EL ÚNICO PASO (cuando te den los $100)

Los créditos se aplican al Org ID — si llegan a TU org, la key actual ya los
usa. Si te dan una key nueva: pega en `.env` la línea `ANTHROPIC_API_KEY=` y:

```bash
perl -pi -e 's/^FABLE_ENABLED=0/FABLE_ENABLED=1/' .env && grep -n FABLE_ENABLED .env
```

(la salida debe decir `FABLE_ENABLED=1`)

```bash
uv run --project orchestrator python simcolombia/fable/showtime.py ping
```

Si el ping contesta: estamos en el aire. TODO lo demás ya está precableado.

## LAS DOS PANTALLAS

- Proyector: https://build-day-danis-project.vercel.app/sim (y `/` para el visor
  del enjambre — Fable aparece ahí con su barra coral y su gasto en vivo).
- Terminal local: los comandos de abajo (streaming en vivo — Fable piensa en
  minutos, deja que el público lo VEA pensar).

## EL PROGRAMA (orden REAL de escena: el duelo va temprano a propósito — mueve
## al público antes de la parte densa)

**PASO PREVIO** (una sola vez, ~$2.15 la primera lectura):
```bash
uv run --project orchestrator python simcolombia/fable/showtime.py pais serialize
```

**ESCENA 1 · "Se leyó a Colombia entera"** (~$2.5 + 5¢ por relectura):
```bash
uv run --project orchestrator python simcolombia/fable/showtime.py pais "Te acabas de leer un país entero: 6.600 personas, 33 territorios, todas sus deliberaciones de hoy. Preséntate y di tres cosas que viste que nosotros no."
```
Preguntas del público SIN pelear con comillas ni tildes en el shell:
```bash
uv run --project orchestrator python simcolombia/fable/showtime.py preguntar
```
(abre un micrófono: se escribe la pregunta, enter, Fable responde; vacío = salir)

**ESCENA 2 · El duelo ciego** (~$12):
```bash
uv run --project orchestrator python simcolombia/fable/showtime.py duelo
```
Mientras corre: voto a mano alzada. Protocolo fijo: 6 retos (3 fáciles/3 duros),
el juez Jev va ciego con orden aleatorizado y longitud controlada; si un lado no
responde, ese reto se ANULA (se dice en voz alta). Desempate: el público.

**ESCENA 3 · El auditor** (~$30 — verdad.json YA está, con fuentes primarias):
```bash
uv run --project orchestrator python simcolombia/fable/showtime.py auditor
```

**ESCENA 4 · El forense** (relee el caché → centavos):
```bash
uv run --project orchestrator python simcolombia/fable/showtime.py forense
```

**ESCENA 5 · Colombia 2050** (la población YA está generada; el prompt se arma
solo con celdas DANE reales — nada de pegar JSON en vivo):
```bash
uv run --project orchestrator python simcolombia/fable/showtime.py pais 2050
```

**ESCENA 6 · El director de orquesta** (Fable al mando del enjambre, visor
proyectado):
```bash
uv run --project orchestrator python orchestrator/swarm.py "Analiza las 3 conclusiones más divididas del modo país de hoy y propone la pregunta que reconciliaría a los territorios"
```

## ADVERTENCIAS PARA DECIR EN ESCENA (rigor = puntos)
- 2050 es efecto de composición (cohortes envejecidas), no valores futuros —
  y los residentes lo demuestran: los "mayores" de 2050 se llaman Katherine y
  Jhon Wilmer, la cohorte de los 90 con canas.
- Varianza sintética artificialmente baja (Bisbee): corrimientos, no verdades.
- El duelo va ciego, aleatorizado y con longitud controlada (Zheng/MT-Bench).

## SI ALGO SE CAE
- Web caída → todo corre local: `python3 -m http.server 8377 --directory dashboard`
  y en el navegador: http://localhost:8377/ (visor) · http://localhost:8377/sim/ (sim).
- Fable lento → es normal (minutos); el streaming ES el espectáculo.
- `stop_reason: refusal` → reformular en una frase; sigue el show.
- Un 429/529 a mitad de acto → el cliente reintenta solo (max_retries=2).
- Acto ya corrido que hay que re-mostrar (o Fable caído del todo):
  ```bash
  uv run --project orchestrator python simcolombia/fable/showtime.py replay pais
  ```
  (cada acto `pais`/`preguntar` queda grabado en `simcolombia/fable/cache/` y el
  replay lo re-transmite con ritmo de streaming, gratis; `replay` a secas lista
  lo grabado)

## LA FRASE DE CIERRE
"Esta mañana no existía nada de esto. Un ejército de agentes de $0.15/M
construyó un país con el censo real. Esta noche, Fable 5.1 se lo leyó ENTERO
de una sentada, nos dijo dónde miente, cómo delibera mal, y qué opinará cuando
envejezca. Eso es hasta dónde llega el modelo."
