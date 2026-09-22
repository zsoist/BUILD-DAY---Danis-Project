#!/usr/bin/env bash
# ¿Quedó bien cerrado Supabase?
#
# Corre las tres pruebas que importan contra tu proyecto real. Lee las
# credenciales de .env — nunca las pongas aquí.
#
#   ./seguridad/comprobar.sh
#
# Esperado DESPUÉS de aplicar seguridad/cerrar_supabase.sql:
#   leer    401    ← nadie lee tus datos con la llave pública
#   borrar  401    ← nadie los borra
#   insertar 201   ← el enjambre y el simulador siguen escribiendo
#
# El borrado se prueba con un id imposible: no toca ninguna fila real.
set -u
cd "$(dirname "$0")/.."

[ -f .env ] || { echo "⛔ no encuentro .env"; exit 1; }
U=$(grep -E '^SUPABASE_URL=' .env | cut -d= -f2- | tr -d '"'"'"' ')
K=$(grep -E '^SUPABASE_PUBLISHABLE_KEY=' .env | cut -d= -f2- | tr -d '"'"'"' ')
[ -n "$U" ] && [ -n "$K" ] || { echo "⛔ falta SUPABASE_URL o SUPABASE_PUBLISHABLE_KEY en .env"; exit 1; }

echo "proyecto: ${U#https://}"
echo

fallos=0
for t in army_events sim_calls sim_encuestas profiles; do
  leer=$(curl -s -o /dev/null -w '%{http_code}' \
    "$U/rest/v1/$t?select=*&limit=1" -H "apikey: $K")
  borrar=$(curl -s -o /dev/null -w '%{http_code}' -X DELETE \
    "$U/rest/v1/$t?id=eq.-999999999" -H "apikey: $K")

  printf '  %-15s leer %s   borrar %s   ' "$t" "$leer" "$borrar"
  if [ "$leer" = "200" ] || [ "$borrar" = "204" ]; then
    echo "⛔ ABIERTA"; fallos=$((fallos+1))
  else
    echo "✓ cerrada"
  fi
done

echo
if [ "$fallos" -gt 0 ]; then
  echo "⛔ $fallos tabla(s) siguen abiertas — aplica seguridad/cerrar_supabase.sql"
  exit 1
fi
echo "✓ todo cerrado. Falta confirmar que el enjambre SÍ puede escribir:"
echo "  corre una tarea corta y mira que aparezca en el visor."
