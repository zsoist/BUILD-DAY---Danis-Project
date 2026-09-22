# Experimento «¿son personas reales?»

A/B con grupo de control sobre las MISMAS personas y la MISMA pregunta:

- **A** = andamiaje de producción. Los prompts se extraen del `index.html` vivo
  (no hay copia que se desincronice): `persona()` + `sondeoInstr()`.
- **B** = control desnudo: "eres un colombiano de X años, oficio Y, de Z".

La diferencia entre lotes **es** el andamiaje. Semilla fija → reproducible.
Corre sobre DeepSeek; jamás toca la API de Anthropic.

```bash
node scripts/experimento/generar.mjs 28 "tu pregunta" /tmp/exp.json
python3 scripts/experimento/medir.py /tmp/exp.json
```

Las métricas son deterministas y se calculan en Python sobre el texto crudo:
índice de manada (4-gramas propios, excluyendo el vocabulario de la pregunta),
diversidad léxica, arranques distintos, variación de largo, señal de educación
(¿se oye el nivel educativo de la ficha?), obediencia al libreto asignado,
y **V de Cramér identidad→opinión**, la métrica de caricatura de la literatura.

Ningún número lo juzga un modelo de lenguaje.

Ver `METODO.md` en la raíz para resultados y contexto científico.
