# simcolombia/ — de dónde salen las personas

8.000 personas sintéticas en 33 departamentos (85 a 875 según población). Cada
una es una persona real de la GEIH del DANE (13 meses de microdatos), repesada
con proyecciones DANE 2026. Método y resultados: `docs/METODO.md`.

## Pipeline

| Script (`pipeline/`) | Produce |
|---|---|
| `download_dane.py`, `download_v2.py` | microdatos en `data/raw_v2/` (5.2 GB, ignorado por git) |
| `build_marginals.py`, `build_pool_geih.py` | `data/marginals.json`, `data/pool_geih.json.gz` |
| `generate_population_v2.py` | `web/residents_v2.json` — lo que carga el sitio |
| `generate_population.py` | `web/residents.json` — respaldo si falla el v2 |
| `validar_v2.py` | `web/validacion_v2.json`; sale 1 si algún marginal no cuadra |

```bash
uv run python simcolombia/pipeline/validar_v2.py   # Python 3.12, entorno en la raíz
```

`data/`: `marginals.json`, `pool_geih.json.gz`, `perfiles_politicos_2018.json`,
`dossiers/dossier_*.json` (33, contexto por departamento), `ecp2023_codebook.json`
(para el careo contra la ECP).

## Reglas

- Números en Python, nunca estimados por un modelo. Cada cifra, trazable a su
  archivo del DANE.
- Tras regenerar la población, corre `validar_v2.py` a mano: el despliegue no
  tiene paso de build que lo haga por ti.
- La ECP 2023 no genera personas: es contra lo que se comparan las respuestas.
