#!/usr/bin/env bash
# ¿Hay alguna credencial a punto de entrar al repo?
#
#   ./seguridad/barrer.sh          # antes de commitear
#
# POR QUÉ EXISTE: el barrido obvio es `git grep`, y tiene un hueco que nos
# mordió el 2026-09-22. git grep solo mira archivos RASTREADOS, así que un
# archivo con una llave real que todavía no está en el índice —o que acabas de
# mover a una ruta nueva que .gitignore ya no cubre— le pasa por debajo. Lo
# frenó la protección de GitHub, que es la última red, no la primera.
#
# Aquí se barre el ÁRBOL ENTERO y después se pregunta, archivo por archivo, si
# git lo ignora. Un archivo con llave está bien solo si está ignorado.
set -u
cd "$(dirname "$0")/.."

# Prefijos reales de proveedor. No se busca "sk-" a secas: aparece en
# documentación, en marcadores y en ejemplos, y un barrido que grita siempre
# deja de leerse.
PATRON='sk-or-v1-[A-Za-z0-9]{20,}|sk-ant-api[0-9]{2}-[A-Za-z0-9_-]{20,}|sk-[a-f0-9]{32}|sb_secret_[A-Za-z0-9_-]{10,}|gh[pousr]_[A-Za-z0-9]{36}'

problemas=0
while IFS= read -r f; do
  if git check-ignore -q "$f"; then
    printf '  · %-44s ignorado ✓\n' "$f"
  else
    printf '  ⛔ %-44s NO IGNORADO\n' "$f"
    problemas=$((problemas+1))
  fi
done < <(grep -rIlE "$PATRON" . \
           --exclude-dir=.git --exclude-dir=node_modules \
           --exclude-dir=runs --exclude-dir=__pycache__ 2>/dev/null)

echo
if [ "$problemas" -gt 0 ]; then
  echo "⛔ $problemas archivo(s) con credencial fuera de .gitignore."
  echo "   Añádelos a .gitignore. Si ya los commiteaste, la llave hay que ROTARLA:"
  echo "   quitarla del repo no la desexpone."
  exit 1
fi
echo "✓ ninguna credencial expuesta"

# Segunda red: lo que está a punto de commitearse, mirado por separado. Un
# archivo puede estar ignorado y aun así haber entrado al índice con -f.
if git diff --cached --quiet 2>/dev/null; then exit 0; fi
enIndice=$(git diff --cached --name-only | while read -r f; do
  [ -f "$f" ] && grep -lE "$PATRON" "$f" 2>/dev/null; done)
if [ -n "$enIndice" ]; then
  echo
  echo "⛔ y además está EN EL ÍNDICE, listo para commitear:"
  echo "$enIndice" | sed 's/^/     /'
  exit 1
fi
