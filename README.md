# ColombIA ¡Que Piensa!

Simulador de opinión pública colombiana. Escoges departamento, preguntas, responden.
**No es una encuesta**: no tiene margen de error. No se usa para campañas ni segmentación de votantes.

## Estructura

| Ruta | Contenido |
|---|---|
| `web/` | el sitio que despliega Vercel |
| `api/opina.js` | única función de servidor; guarda la llave |
| `lib/filtro.mjs` | filtro de salida del proxy (copiado dentro de `api/opina.js`; una prueba avisa si difieren) |
| `simcolombia/` | microdatos del DANE y su procesamiento |
| `scripts/experimento/` | cómo sabemos si sirve |
| `seguridad/` | barrido de credenciales, batería de inyección, cierre de Supabase |
| `docs/` | `METODO.md`, `PRODUCT.md`, `OPENROUTER.md` |

## Correrlo

Local: `cd web && python3 -m http.server 8377`. Sin backend pide la llave de OpenRouter en Ajustes, o la lee de `web/assets/local_keys.json` (ignorado por git).

Vercel: `vercel.json` ya apunta a `web/`. Variables:

| Variable | Valor |
|---|---|
| `OPENROUTER_API_KEY` | obligatoria |
| `ALLOWED_ORIGINS` | tus dominios, separados por coma |
| `OPENROUTER_DAILY_USD` | `10` |
| `MAX_TOKENS_TECHO` | `260` |
| `MODELOS_VOZ` | `deepseek/deepseek-v4.1-flash,z-ai/glm-5.3-flash` |
| `OR_MAX_PROMPT` / `OR_MAX_COMPLETION` | `1.0` / `3.0` USD por millón |
| `SITE_URL` | la del sitio |

Supabase es opcional y solo para telemetría: aplica antes `seguridad/cerrar_supabase.sql` (deja las tablas en solo-insertar) y comprueba con `./seguridad/comprobar.sh`.

## Las personas

8.000 personas sintéticas en 33 departamentos (de 85 a 875 según población). Cada una es una persona real encuestada por el DANE en la GEIH (13 meses de microdatos), repesada con proyecciones DANE 2026. La ECP 2023 del DANE (46.392 adultos reales) no es la fuente de las personas: es contra lo que se comparan las respuestas.

## Qué modelo y por qué

Voces: `deepseek/deepseek-v4.1-flash`; respaldo `z-ai/glm-5.3-flash`. Todo por OpenRouter.
DeepSeek gana 3 de 5 preguntas y empata 2 contra la ECP. Detalle: `docs/OPENROUTER.md`.

## Los fallos medidos

| Fallo | Estado |
|---|---|
| Sub-dispersión (voces demasiado parecidas) | en escalas 1-5, SSR la corrige (desviación 0.77 → 0.98; igual sin libreto). **Aún no está en el sitio** |
| SSR en preguntas de sí/no | mejora modesta (error 9.6 vs 12.0 pts, 8 ítems) pero infla el "sí" ~20 pts en rechazos casi unánimes: no se despliega |
| Postura asignada por hash (libreto 40/40/20) | efecto pequeño: el modelo la ignora en temas de consenso |
| Termómetro 0-100 en vez de escala | descartado: empeoró el W1 de 0.084 a 0.154 |
| IRTree | descartado: holdout W1 0.272, peor que el azar |
| Sesgo de GLM | 38% en "muy insatisfecho" donde los humanos ponen 18%; por eso es respaldo |

Cómo se mide: `scripts/experimento/README.md`. Método: `docs/METODO.md`.

## Seguridad

```bash
./seguridad/barrer.sh                                # antes de cada commit
node --test seguridad/filtro.test.mjs                # 36 pruebas
node seguridad/inyeccion.mjs --url <tu-dominio>/api/opina --origen <tu-dominio>
```

La batería de inyección lanza 34 ataques. Última medición contra producción: 32 contenidos, 1 marcado que resultó ser una voz negándose, 1 indeterminado.

## Enjambre de agentes

Vive en su propio repo, no copia este:

```bash
uvx --from git+https://github.com/zsoist/SWARMS enjambre "tarea"
uvx --from git+https://github.com/zsoist/SWARMS enjambre-visor
```

Lee el `.env` de aquí y escribe `runs/` aquí.

Python 3.12, entorno en la raíz: `uv run python <script>`.