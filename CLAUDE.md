# CLAUDE.md

ColombIA ¡Que Piensa!: 8.000 personas sintéticas (cada una, una persona real de
la GEIH del DANE) que opinan; se comparan contra la ECP 2023 (46.392 adultos).
Producto y límites: `README.md`, `docs/PRODUCT.md`. Método: `docs/METODO.md`.

## Mapa

| Ruta | Qué | Se despliega |
|---|---|---|
| `web/` | el sitio: `index.html` (lógica) + `escena.js` (escenario 3D) + datos | sí (Vercel) |
| `web/escenas/`, `web/gente/` | 17 fondos y 47 personajes pixel (HD-2D), generados | sí |
| `scripts/escena/` | generar imágenes (OpenRouter) y recortar hojas de personajes | no |
| `api/opina.js` | única función; proxy a OpenRouter | sí |
| `lib/filtro.mjs` | filtro de salida; **copiado** dentro de `api/opina.js` | no |
| `simcolombia/` | pipeline de datos del DANE (ver su CLAUDE.md) | no |
| `scripts/experimento/` | careo contra la ECP, SSR | no |
| `seguridad/` | barrido, batería de inyección, cierre de Supabase | no |

El enjambre NO vive aquí: `github.com/zsoist/SWARMS`. Se usa sobre esta carpeta
(lee `.env`, escribe `runs/`):

```bash
uvx --from git+https://github.com/zsoist/SWARMS enjambre "tarea"      # o --plan plan.json
uvx --from git+https://github.com/zsoist/SWARMS enjambre-visor        # localhost:8777
```

## Comandos

```bash
cd web && python3 -m http.server 8377               # sitio local
uv run python simcolombia/pipeline/validar_v2.py    # Python 3.12, entorno en la raíz
node --test seguridad/filtro.test.mjs               # antes de tocar el filtro
node --test scripts/experimento/anclas.test.mjs     # antes de tocar la estimación del sondeo
./seguridad/barrer.sh                               # antes de CADA commit
```

## Reglas, cada una por algo que ya pasó

- **Secretos solo en `.env`.** Los dos repos son públicos. `barrer.sh` barre el
  árbol entero: `git grep` solo ve lo rastreado y casi se publica una llave al
  mover un archivo.
- **Números en Python, nunca de un modelo.** Métricas, conteos, costos.
- **Anthropic apagado** (`FABLE_ENABLED=0`). Topes: $10 OpenRouter, $10 DeepSeek.
- **`api/opina.js` sin imports.** Un `import` desde `lib/` tumbó la función en
  Vercel (`FUNCTION_INVOCATION_FAILED`). Si cambias el filtro, cámbialo en
  `lib/filtro.mjs`, cópialo entre los marcadores `filtro:inicio/fin`, y corre
  el test: falla si las copias difieren.
- **Antes de desplegar el proxy, invócalo en local** con una petición simulada
  (`cp api/opina.js /tmp/x.mjs` e importar el handler). Después de desplegar,
  confirma la versión con una petición que distinga (ej. 17 mensajes → 400).
- **Razonamiento explícito y por modelo.** DeepSeek `{enabled:false}`; GLM
  `{effort:"low"}` (GLM rechaza apagarlo; omitirlo cuesta 3×; `effort:"low"` en
  DeepSeek dio 5/6 respuestas vacías). Nunca el arreglo `models` entre los dos:
  manda el mismo cuerpo a ambos. Detalle: `docs/OPENROUTER.md`.
- **Nunca copies el enjambre de vuelta aquí.** Dos copias a mano rompieron
  SWARMS dos veces en un día.
- **Nada que cambie lo que ve la gente sin medirlo contra la ECP.** Regla de
  despliegue fijada antes de ver datos y probada en ítems que no se usaron
  para calibrar (ver `docs/METODO.md`, mezcla). SSR solo parecía mejor y
  habría dicho "30% apoya invadir propiedad" (real: 11%).
- **El prompt de la voz empieza por lo que es igual para todas** (`ORDEN_CACHE`):
  así el proveedor lo cachea. Texto propio de cada persona, después de las reglas.
- **`escena.js` solo muestra; no decide.** La lógica medida vive en `index.html`
  (el careo la extrae de ahí). Diseño: `DESIGN.md`.
- **Docs cortos.** Tabla antes que párrafo. Si no cambia lo que alguien haría, fuera.

## Modelos (medidos, no por marca)

| Uso | Modelo | Por qué |
|---|---|---|
| voces | `deepseek/deepseek-v4.1-flash` vía DeepInfra | gana 3/5 y empata 2 contra la ECP; ~$0.0003 por voz con caché |
| respaldo de voces | `z-ai/glm-5.3-flash` | colapsa más (38% en una opción vs 18% real) |
| enjambre | `z-ai/glm-5.3-flash` | 0% respuestas vacías vs 17% |
| juez | `typesafe/jev-1.13` | ~$0.00002; prosa (8/8) y "¿preguntan lo mismo?" (0 anclas falsas), no datos (0/7) |

Los LLM (todos los probados) creen que en Colombia nada funciona y no se corrigen
infiriendo; sí adoptan una postura dicha. Por eso el sondeo ancla en la respuesta
real de un donante de la ECP cuando el DANE ya hizo la pregunta, o sorteando
de los agregados de LAPOP/Latinobarómetro (`web/opinion/`). Si nadie la midió,
cada voz recibe una postura sorteada con la estimación de un analista (acción
`estimar`): como analista el modelo casi no es pesimista; como persona, sí. Si cambias
`donantes_ecp.py`, `banco_ecp.py` o `fuentes_opinion.py`, regenera y vuelve a medir.
**LAPOP/LB: a `web/` y a git solo agregados** (celdas ≥10); los microdatos y lo
que sale por persona se quedan en `simcolombia/data/raw_v2/`.

## Seguridad del proxy: lo que aguanta y lo que no

Un endpoint público sin login no se cierra del todo: lo que el navegador tiene,
lo tiene cualquiera. Capas vigentes: el servidor pone su propio `system` al
principio y al final y degrada el del cliente; tope de 16 mensajes; filtro de
salida; tope real de gasto leído de `/api/v1/key` de OpenRouter (el contador en
memoria es por instancia). Última batería: 32/34 contenidos.

## Pendiente de Daniel (panel de OpenRouter)

- La llave tiene tope de $10 **de por vida** y caduca el 28 sep 2026: ponerle
  reinicio diario.
- Separar la llave del sitio de la del enjambre.
