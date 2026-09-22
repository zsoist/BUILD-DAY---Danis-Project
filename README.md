# ColombIA ¡Que Piensa!

**Un país sintético al que le puedes preguntar cualquier cosa.**

Cuarenta y siete mil personas sintéticas construidas sobre el censo y las
encuestas del DANE. Escoges un departamento o el país entero, haces una
pregunta, y responden como responderían: con su edad, su educación, su
estrato, su región y sus contradicciones.

No es una encuesta. Es una simulación, y la diferencia importa —está explicada
abajo y repetida en la propia herramienta.

```
https://<tu-dominio>        →  la herramienta, abierta a quien llegue
```

---

## Qué hay aquí

| Carpeta | Qué es |
|---|---|
| `web/` | **El sitio.** Lo que se despliega. Un solo HTML y sus datos |
| `api/opina.js` | La única función de servidor: habla con el modelo y guarda la llave |
| `simcolombia/` | De dónde salen las personas: microdatos del DANE y su procesamiento |
| `scripts/experimento/` | **Cómo sabemos si esto sirve.** El careo contra la realidad |
| `seguridad/` | Barrido de credenciales y cierre de la base de datos |
| `enjambre/` `orchestrator/` `dashboard/` | Herramienta interna de trabajo, no se despliega (ver abajo) |

---

## Correrlo en tu propia infraestructura

Todo el proyecto vive en tres servicios y ninguno es obligatorio para probarlo
en local.

### 1. En tu máquina, sin nada

```bash
cd web && python3 -m http.server 8377
```

Abre `localhost:8377`. Sin función de servidor, la herramienta pide una llave
de OpenRouter en Ajustes y la guarda **en tu navegador**. Si prefieres no
teclearla cada vez, ponla en `web/assets/local_keys.json`:

```json
{ "openrouter": "sk-or-v1-…" }
```

Ese archivo está en `.gitignore` a propósito: **nunca se versiona ni se
despliega**. Antes de cualquier commit, `./seguridad/barrer.sh` comprueba que
no se te haya colado ninguna credencial.

### 2. Vercel

El repo ya trae `vercel.json` apuntando a `web/`. Importas el repo y pones
estas variables de entorno:

| Variable | Para qué | Obligatoria |
|---|---|---|
| `OPENROUTER_API_KEY` | la única llave de modelo que hace falta | sí |
| `OPENROUTER_DAILY_USD` | tope de gasto del día, por defecto 10 | no |
| `ALLOWED_ORIGINS` | tus dominios, separados por coma | sí |
| `MAX_TOKENS_TECHO` | techo de tokens por respuesta, por defecto 260 | no |
| `APP_TOKEN` | si lo pones, el proxy se cierra a quien no lo traiga | no |
| `SUPABASE_URL` + `SUPABASE_PUBLISHABLE_KEY` | telemetría de uso | no |

**Una sola llave.** El proyecto habla con DeepSeek, GLM o cualquier otro modelo
a través de OpenRouter, así que cambiar de modelo es cambiar un nombre, no una
integración.

### 3. Supabase (opcional)

Solo guarda telemetría: cuánto se gastó y qué se preguntó. La herramienta
funciona sin ella. Si la usas, aplica primero
[`seguridad/cerrar_supabase.sql`](seguridad/cerrar_supabase.sql): deja las
tablas en **solo insertar**, porque la llave del navegador es pública por
diseño y sin eso cualquiera podría leer o borrar lo guardado. Comprueba con
`./seguridad/comprobar.sh`.

### 4. Cloudflare

Apuntas el dominio a Vercel y añades el dominio a `ALLOWED_ORIGINS`. Nada más.

---

## Qué modelo usa y por qué

Enrutamos por medición, no por marca. Todo pasa por OpenRouter:

| Para qué | Modelo | El número que lo decide |
|---|---|---|
| Las voces del simulador | `deepseek-flash` | gana 3 de 5 preguntas y empata 2 contra los datos del DANE |
| El enjambre de trabajo | `z-ai/glm-5.3-flash` | 0% de respuestas vacías contra 17% de DeepSeek Flash |
| El juez barato | `typesafe/jev-1.13` | ~$0.00002 por revisión |

El mismo rasgo que hace a GLM fiable escribiendo código lo hace malo fingiendo
desacuerdo: colapsa hacia la respuesta más probable. No hay un modelo mejor,
hay tareas distintas. La evidencia y sus límites están en
[`scripts/experimento/README.md`](scripts/experimento/README.md).

---

## Honestidad sobre qué es esto

**No es una encuesta y no tiene margen de error.** Son modelos de lenguaje
imitando a personas, y eso falla de maneras conocidas que medimos en vez de
esconder:

- **Sub-dispersión**: las voces sintéticas solían opinar más parecido entre sí
  que los colombianos reales. Se corrigió con SSR —la persona habla libre y la
  escala se reconstruye después— y la razón de desviación pasó de 0.77 a 0.98,
  donde 1.00 es lo ideal.
- **Sesgo**: aun con la dispersión correcta, un modelo puede estar
  sistemáticamente corrido. GLM pone el 38% de las voces en "muy insatisfecho"
  donde los humanos ponen el 18%.
- **Caricatura**: que la identidad demográfica prediga la opinión *más* de lo
  que la predice en gente real.

Todo esto se mide contra la Encuesta de Cultura Política 2023 del DANE:

```bash
node scripts/experimento/careo_ecp.mjs 160 P5301 /tmp/libre.json libre
uv run --with pyreadstat --with pandas --python 3.12 python scripts/experimento/ssr.py /tmp/libre.json
```

**No se usa para campañas ni para segmentar votantes.** El método completo está
en [`METODO.md`](METODO.md).

---

## La herramienta interna

`enjambre/`, `orchestrator/` y `dashboard/` son el enjambre de agentes con el
que se construyó buena parte de esto: un modelo bueno reparte el trabajo,
varios baratos lo ejecutan en paralelo, un juez de centavos revisa.

No se despliega y no tiene nada que ver con ColombIA. Vive empaquetado y
aparte en **[zsoist/SWARMS](https://github.com/zsoist/SWARMS)**; aquí queda
para trabajar en local:

```bash
python enjambre/servir.py        # el visor, en localhost
```
