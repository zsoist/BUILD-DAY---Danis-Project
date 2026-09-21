# El reto de esta noche — propuesta de Fable

APIs verificadas HOY 2026-09-21 (responden sin key, listas para agentes):

| Fuente | Qué trae | Endpoint probado |
|---|---|---|
| USGS | Sismos Colombia en vivo e histórico 1900-hoy (hoy: M4.5 San Antonio) | `earthquake.usgs.gov/fdsnws/event/1/query` (bbox CO) |
| GBIF | 40.7M registros de biodiversidad de Colombia, con tiles de mapa | `api.gbif.org/v1/occurrence/search?country=CO` |
| IDEAM | Precipitación `s54a-sgyg`, Temperatura `sbwg-7ju4`, Estaciones `hp9r-jxuu` | `www.datos.gov.co/resource/<id>.json` |
| SECOP | Contratación pública (quién, cuánto, dónde) | `www.datos.gov.co/resource/jbjy-vk9h.json` |

Descartadas por fricción: OpenAQ y NASA FIRMS (piden key), feed del SGC (muerto).

## IDEA A — "COLOMBIA VIVA" ⭐ recomendada

**El pitch:** un visor del pulso natural de Colombia — sismos, lluvia, temperatura,
biodiversidad — que **el enjambre construye solo, en vivo, frente al público**,
módulo por módulo, mientras el army dashboard muestra la obra.

- 4 módulos = 4 frentes paralelos. Cada módulo: un agente builder escribe
  fetcher+visual, un agente runner LO EJECUTA contra la API real, y el error real
  vuelve al builder (loop de auto-corrección con evidencia, no opinión). Jev
  aprueba cada pieza. Fable: plan maestro, revisión entre rondas, ensamblaje.
- Módulo estrella: sismos — el M4.5 de HOY aparece apenas carga.
- Dos pantallas en la demo: (1) army dashboard viendo trabajar al enjambre,
  (2) Colombia Viva armándose y quedando útil.
- Por qué gana: real, útil, visual, colombiano, y el "wow" no es el visor —
  es verlo nacer solo.

## IDEA B — "¿Dónde tiembla Colombia?"

Memoria sísmica 1900-2026 con USGS: mapa temporal animado, el Nido de
Bucaramanga, Armenia 1999, "¿tiembla más ahora o solo medimos más?" (análisis de
agentes con thinking high). Enfocada y profunda, menos paralelismo. **Plan B si
la noche se acorta — o módulo 1 de la Idea A.**

## IDEA C — "La plata pública" (SECOP)

Impacto social alto, pero data sucia y semántica delicada para 3 horas con
público. Descartada para hoy; anotada para después.

## Estructura de las 3 horas (Idea A)

1. **0:00-0:20** — Fable 5.1 entra al mando (`FABLE_ENABLED=1`): plan maestro.
2. **0:20-2:00** — enjambre construye los 4 módulos con loops builder↔runner;
   rondas de Fable re-priorizando según scores de Jev.
3. **2:00-2:40** — ensamblaje, pulido visual, deploy (push → Vercel automático).
4. **2:40-3:00** — demo de 2 min ensayada + parte de gasto de los $100.

## Prep pendiente de aprobación de Daniel

- [ ] Upgrade del harness: gate de EJECUCIÓN (runner que corre el código del
      builder y devuelve stderr al prompt) — el "loop de oro" para agentes coderos.
- [ ] Plan JSON borrador de Colombia Viva con los endpoints ya verificados.
