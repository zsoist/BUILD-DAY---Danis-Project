# simcolombia/ — Sim Colombia

Gemelo poblacional sintético de Colombia (patrón Sim Francisco, 2° puesto Build
Day Opus 4.8) con datos REALES del DANE. Reto del Build Day Bogotá 2026-09-21.

## Arquitectura

```
pipeline/download_dane.py     baja fuentes reales → data/raw/ (gitignored)
pipeline/build_marginals.py   normaliza → data/marginals.json (por departamento:
                              población, sexo, edad x5, urbano/rural, PIB pc, salud)
pipeline/generate_population.py  residentes sintéticos que REPRODUCEN los
                              marginales → dashboard/sim/residents.json
dashboard/sim/index.html      visor: pirámide real vs sintética por dpto +
                              "pregúntale a los residentes" (encuesta LLM en vivo)
```

## División de trabajo (quién valida qué)

- **Python (determinista)**: que los sintéticos cuadren con los marginales reales
  — reporte de error % por dpto/sexo/edad. La estadística NUNCA se le pide a un LLM.
- **Ejército DS**: dossiers narrativos por departamento (contexto cultural,
  economía, habla) que dan carne a los residentes. Prompts con los números reales.
- **Jev**: gate de los dossiers — verosímil, sin estereotipos, fiel a los números.
- **Fable 5.1 (evento, $100)**: demógrafo jefe — audita la población sintética,
  la interroga, encuentra dónde se rompe contra la realidad. El Breakthrough.

## Reglas

- Fuente real o nada: cada número trazable a su dataset (DANE/datos.gov.co).
- Residentes: ~100 por departamento (33 unidades: 32 dptos + Bogotá D.C.).
- Encuesta en vivo: muestrear N residentes del dpto, cada uno responde EN PERSONAJE
  (persona = atributos censales + dossier), agregación con conteo transparente.
- Sesgos: los residentes opinan como PERSONAJES VEROSÍMILES, no como caricaturas;
  disclaimer visible de que es simulación.
