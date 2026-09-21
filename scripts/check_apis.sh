#!/bin/bash
# Smoke test de las 3 APIs del Build Day. Corre desde la raíz: ./scripts/check_apis.sh
set -uo pipefail
cd "$(dirname "$0")/.."
set -a; source .env; set +a

pass=0; fail=0
ok()  { echo "  ✅ $1"; pass=$((pass+1)); }
bad() { echo "  ❌ $1"; fail=$((fail+1)); }

echo "1/3 Anthropic (Fable ${FABLE_MODEL:-claude-fable-5-1})…"
if [ "${FABLE_ENABLED:-0}" != "1" ]; then
  echo "  ⏭  saltado — FABLE_ENABLED=0 (Fable solo con autorización explícita, \$\$\$)"
else
ws_header=()
[ -n "${ANTHROPIC_WORKSPACE_ID:-}" ] && ws_header=(-H "anthropic-workspace-id: $ANTHROPIC_WORKSPACE_ID")
r=$(curl -sS --max-time 30 https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" "${ws_header[@]}" \
  -H "anthropic-version: 2023-06-01" -H "content-type: application/json" \
  -d "{\"model\":\"${FABLE_MODEL:-claude-fable-5-1}\",\"max_tokens\":16,\"messages\":[{\"role\":\"user\",\"content\":\"Di OK\"}]}")
echo "$r" | grep -q '"type":"message"' && ok "Anthropic responde" || bad "Anthropic: $r"
fi

echo "2/3 DeepSeek (deepseek-flash)…"
r=$(curl -sS --max-time 30 "$DEEPSEEK_BASE_URL/chat/completions" \
  -H "Authorization: Bearer $DEEPSEEK_API_KEY" -H "Content-Type: application/json" \
  -d '{"model":"deepseek-flash","max_tokens":16,"messages":[{"role":"user","content":"Di OK"}]}')
echo "$r" | grep -q '"choices"' && ok "DeepSeek responde" || bad "DeepSeek: $r"

echo "3/3 OpenRouter…"
r=$(curl -sS --max-time 30 "$OPENROUTER_BASE_URL/chat/completions" \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" -H "Content-Type: application/json" \
  -d '{"model":"deepseek/deepseek-v4.1-flash","max_tokens":16,"messages":[{"role":"user","content":"Di OK"}]}')
echo "$r" | grep -q '"choices"' && ok "OpenRouter responde" || bad "OpenRouter: $r"

echo
echo "Resultado: $pass OK, $fail fallando"
exit $fail
