# ColombIA ¡Que Piensa!

47 mil personas sintéticas sobre microdatos del DANE. Escoges departamento,
preguntas, responden. **No es una encuesta**: no tiene margen de error.

## Estructura

| Ruta | Qué |
|---|---|
| `web/` | el sitio (lo que Vercel despliega) |
| `api/opina.js` | única función de servidor; guarda la llave |
| `simcolombia/` | microdatos del DANE y su procesamiento |
| `scripts/experimento/` | cómo sabemos si sirve |
| `seguridad/` | barrido de credenciales y cierre de Supabase |
| `enjambre/` `orchestrator/` `dashboard/` | herramienta interna, no se despliega — [zsoist/SWARMS](https://github.com/zsoist/SWARMS) |

## Correrlo

```bash
cd web && python3 -m http.server 8377     # local, sin backend
```

Sin backend pide llave de OpenRouter en Ajustes, o la lees de
`web/assets/local_keys.json` (ignorado por git, nunca se despliega).

En Vercel: importas el repo (`vercel.json` ya apunta a `web/`) y pones:

| Variable | Por defecto |
|---|---|
| `OPENROUTER_API_KEY` | — obligatoria |
| `ALLOWED_ORIGINS` | tus dominios, separados por coma |
| `OPENROUTER_DAILY_USD` | 10 |
| `MAX_TOKENS_TECHO` | 260 |
| `MODELOS_VOZ` | `deepseek/deepseek-v4.1-flash,z-ai/glm-5.3-flash` |
| `OR_MAX_PROMPT` / `OR_MAX_COMPLETION` | 1.0 / 3.0 (USD por millón) |

Una sola llave: todo pasa por OpenRouter, con respaldo automático entre modelos.

Supabase es opcional (solo telemetría). Si la usas, aplica antes
[`seguridad/cerrar_supabase.sql`](seguridad/cerrar_supabase.sql) —deja las
tablas en solo-insertar— y comprueba con `./seguridad/comprobar.sh`.

## Qué modelo y por qué

Por medición, no por marca. Detalle en
[`scripts/experimento/README.md`](scripts/experimento/README.md).

| Para | Modelo | El número |
|---|---|---|
| voces | `deepseek-flash` | gana 3 de 5 preguntas, empata 2, contra el DANE |
| enjambre | `z-ai/glm-5.3-flash` | 0% de respuestas vacías vs 17% |
| juez | `typesafe/jev-1.13` | ~$0.00002 por revisión |

## Los fallos, medidos

- **Sub-dispersión** — corregida con SSR: razón de desviación 0.77 → 0.98 (1.00 ideal).
- **Sesgo** — GLM pone 38% en "muy insatisfecho" donde los humanos ponen 18%.
- **Caricatura** — que la demografía prediga la opinión más que en gente real.

```bash
node scripts/experimento/careo_ecp.mjs 160 P5301 /tmp/l.json libre
uv run --with pyreadstat --with pandas --python 3.12 python scripts/experimento/ssr.py /tmp/l.json
```

No se usa para campañas ni segmentación de votantes. Método: [`docs/METODO.md`](docs/METODO.md).
