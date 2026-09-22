# OpenRouter — hoja de decisiones interna

## Errores que ya pagamos

| Síntoma | Causa | Prevención |
|---|---|---|
| Mismo prompt: 5.25e-06 con Relace, 7.25e-06 con CoreWeave | El router cambia de proveedor por petición. Con n=7 los costos convergen dentro del 3%, así que es varianza, no una regla | `max_price` como techo; no cuentes con `sort` para abaratar |
| Pedimos JSON estructurado, llega texto libre, sin error | OpenRouter **descarta en silencio** parámetros que el proveedor enrutado no soporta | `require_parameters: true` |
| GLM 5.3 responde 400 `Reasoning is mandatory for this endpoint` al intentar apagar razonamiento | El endpoint exige razonamiento | `reasoning: {effort: 'low'}` → en la práctica 0 tokens de razonamiento |
| DeepSeek Flash: 17% de respuestas vacías en banco de 4 tareas × 3 reps (GLM 5.3 Flash: 0%); las vacías se cobran igual | El razonamiento se come `max_tokens` | `reasoning` explícito por modelo y un intento por modelo (ver abajo) |
| Fallback no actúa | IDs de modelo inválidos dan 400 **antes** de enrutar; el fallback solo cubre fallos en ruta | Validar slugs contra `/models` |
| Voz del sitio (~3.600 tokens de prompt): 6 de 8 a Together ($0.30/M) con `sort: 'price'` | Con prompts largos el router no elige el más barato; con prompts cortos sí | `order: ["deepinfra", …]`: $0.0012 → $0.0003 por voz (fp8 + caché) |
| Caché de prefijo en 0 | El prompt empezaba con lo propio de cada persona | Lo fijo primero (`ORDEN_CACHE` en `web/index.html`): 47% del prompt a $0.0042/M en DeepInfra |
| Cada POST a `/api/opina` rebotaba con 308 (~240 ms) | `trailingSlash: true` en `vercel.json` | El cliente llama a `/api/opina/` |
| Facturación por tokens estimados | Innecesario | `usage.cost` viene gratis en la respuesta; cobrar con eso |

## Opciones de enrutamiento

| Campo | Cuándo usar |
|---|---|
| `require_parameters` | **Siempre true.** Sin él, perdes params en silencio según el proveedor |
| `data_collection: 'deny'` | **Siempre.** Por nuestro proxy viajan preguntas de usuarios |
| `max_price: {prompt, completion}` | Techo por petición en USD/millón de tokens; evita el 38% sorpresa |
| `sort` | **No es palanca de precio** (con prompts largos ni siquiera elige el barato; usa `order`): medido n=7, los tres valores cuestan lo mismo ±3%. Mueve la COLA: latency p_max 1582ms · price 3378ms · throughput 14396ms. Usa `latency` cuando corras en paralelo |
| `models` + `route: 'fallback'` | Solo entre modelos que acepten el MISMO `reasoning`. DeepSeek y GLM no (ver abajo) |
| `only` / `ignore` | Restringir o excluir proveedores concretos |
| `order` / `allow_fallbacks` | **El sitio usa `order`** (DeepInfra, StreamLake, Alibaba; `OR_ORDEN`) con caída permitida. La caché es por proveedor: fijarlo es lo que la hace funcionar |
| `quantizations` | Fijar precisión aceptable (ej. no aceptar int8) |
| `zdr` | Zero data retention si un cliente lo exige |

## Cuerpo de petición que usamos

```json
{
  "model": "z-ai/glm-5.3-flash",
  "messages": [{"role": "user", "content": "..."}],
  "reasoning": {"effort": "low"},
  "provider": {
    "require_parameters": true,
    "data_collection": "deny",
    "max_price": {"prompt": 0.5, "completion": 1.5},
    "sort": "latency"
  },
  "usage": {"include": true}
}
```

- `model` con barra (`z-ai/glm-5.3-flash`) = slug de OpenRouter, decenas de proveedores detrás; sin barra = API nativa del proveedor.
- `reasoning.effort: 'low'`: único modo fiable con GLM 5.3; apagar razonamiento del todo da 400.
- `provider.sort: 'latency'`: este cuerpo es del enjambre; en el sitio público cambiar a `'price'`.
- `usage`: confirma costo real; no volver a estimar tokens para facturar.
- Headers `HTTP-Referer` y `X-Title`: atribución obligatoria en el dashboard.

## Costos

- `usage.cost` llega en cada respuesta sin flags: es la fuente de verdad de facturación.
- Precio por petición varía hasta 38% según proveedor enrutado al mismo modelo: sin `max_price` el gasto no es determinista.
- Respuestas vacías se cobran: monitorear tasa de vacíos por modelo (DeepSeek Flash 17% vs GLM 5.3 Flash 0% en nuestro banco).
## GLM 5.3: el razonamiento es lo que se paga

Medido contra la API, misma pregunta, `max_tokens: 400`:

| `reasoning` | tokens de razonamiento | costo | vs `low` |
|---|---|---|---|
| `{effort:"low"}` | 6 | $0.0000092 | — |
| `{effort:"medium"}` | 2 | $0.0000072 | 0.8× |
| `{effort:"high"}` | 7 | $0.0000097 | 1.1× |
| `{effort:"max"}` | 117 | $0.0000647 | **7×** |
| **omitido** | 43 | $0.0000277 | **3×** |

**Mándalo siempre explícito.** Omitirlo no es "sin razonamiento", es 3× el precio.
La respuesta fue idéntica ("391") en los cinco casos.

## No uses `models` entre DeepSeek y GLM

Con `models` + `route:'fallback'`, OpenRouter manda el MISMO cuerpo a todos
los modelos. Y cada uno necesita su parámetro de razonamiento
(`max_tokens: 128`, 6 llamadas):

| | `{enabled:false}` | `{effort:"low"}` |
|---|---|---|
| `deepseek/deepseek-v4.1-flash` | 1/6 vacías | **5/6 vacías**: razona hasta agotar el presupuesto |
| `z-ai/glm-5.3-flash` | **400 Reasoning is mandatory** | bien |

No hay un cuerpo que sirva a los dos. Hacemos un intento por modelo, cada uno
con su `reasoning`, y un `content` de solo espacios cuenta como vacío y pasa al
siguiente. Primero probamos `effort:"low"` para todos "por compatibilidad" y
las voces salieron en blanco.

## El caché implícito no se activa

Tres llamadas seguidas con el mismo prefijo de ~3.100 tokens, con y sin fijar
proveedor: `cached_tokens` = 0 siempre, costo idéntico. Fijar proveedor con
`allow_fallbacks:false` además devolvió 429 en 2 de 3 intentos.

No cuentes con el caché a través de OpenRouter. Si necesitas descuento por
prefijo, va por la API nativa del proveedor.
