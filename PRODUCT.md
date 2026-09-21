# PRODUCT.md — Army Dashboard (Build Day)

## Qué es
Visor de mando del enjambre: Fable/v4-pro planifica, 8 tropas deepseek-flash ejecutan,
Jev juzga. El dashboard muestra el estado vivo de cada corrida: orden de batalla,
tablero de operaciones (DAG en el tiempo), parte de guerra (eventos), munición
(presupuesto) y veredictos de Jev.

## Usuario y escena
Daniel (comandante) y el público del Build Day. Aula oscura, proyector, laptops.
Se mira de reojo mientras el enjambre trabaja y se proyecta en la demo de 2 min:
debe leerse a 3 metros. Modo: **Operate**.

## Verdad del producto (no inventable)
- Datos reales de `army_events` (Supabase, proyecto DAN GPT) o `feed.json` local.
- Rangos reales: General (Fable 5.1) / Oficial (Opus 5) / 8× deepseek-flash / juez Jev.
- Presupuestos reales: DeepSeek $10, OpenRouter $10, Anthropic $100 (evento).
- Nada de métricas fabricadas: si no hay corrida, estado vacío honesto.

## Compromisos de marca
- Español, wording corto y asertivo (preferencia explícita de Daniel).
- Premium, NO "AI slop": prohibido neon-glow genérico, gradient text, progress rings.
- Mundo visual: puesto de mando / war-room (pinneado por el brief: "army", "general").
- Personalización real: fuente de datos, ritmo de refresco, acento, densidad.

## Supuestos declarados (inferidos del brief, corregibles)
- Oscuro por escena (aula de noche + proyector), no por categoría.
- Una sola pantalla sin scroll en desktop; apilado legible en móvil.
- Corre como archivo estático: local (`python -m http.server`) y Vercel.
