# CLAUDE.md

## Estado
Taller de un día (21 sep 2026, Bogotá), ya realizado. ColombIA ¡Que Piensa!: simulador de opinión pública con 47 mil personas sintéticas sobre microdatos del DANE. Instrucciones de producto en README.md.

## Estructura
| Ruta | Qué es | ¿Se despliega? |
|---|---|---|
| web/ | Frontend en Vercel | Sí |
| api/opina.js | Única función de servidor | Sí |
| enjambre/, orchestrator/, dashboard/ | Enjambre de agentes (código en github.com/zsoist/SWARMS) | No, herramienta interna |

## Entorno
- Python 3.14 con uv; dependencias en orchestrator/pyproject.toml. Todo se corre desde la raíz.
- Los dos repos son PÚBLICOS.

## Secretos
- Credenciales SOLO en `.env` (ignorado). Ignoradas también `web/assets/local_keys.json` y `dashboard/assets/local_keys.json` (respaldo sin Vercel).
- Antes de CADA commit: `./seguridad/barrer.sh`. Motivo: el barrido con `git grep` solo ve archivos RASTREADOS; una llave en archivo nuevo o recién movido pasa. Ya ocurrió y la frenó la protección de GitHub.

## Modelos (todo por OpenRouter; cambiar de modelo = cambiar un nombre)
| Uso | Modelo | Medición |
|---|---|---|
| Voces del simulador | deepseek-flash | Gana 3/5 y empata 2/5 vs datos del DANE |
| Enjambre de trabajo | z-ai/glm-5.3-flash | 0% respuestas vacías vs 17% de DeepSeek Flash |
| Juez barato | typesafe/jev-1.13 | ~0.00002 USD/revisión; 8/8 en prosa, 0/7 verificando datos → solo para prosa |
| Números y estadística | Ningún modelo | Se calculan en Python, determinista |

Flota: `ENJAMBRE=glm` o `ENJAMBRE=deepseek`.

## Costos
- Anthropic apagado por defecto (`FABLE_ENABLED=0`); no encender sin autorización explícita.
- Topes: 10 USD en DeepSeek y 10 USD en OpenRouter.