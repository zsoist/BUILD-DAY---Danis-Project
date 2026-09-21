// /api/opina — el proxy del país sintético.
// Corre en Vercel con las keys en variables de entorno: el navegador nunca ve
// una key. FULL DeepSeek nativo primero; OpenRouter de respaldo.
export default async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
  if (req.method === "OPTIONS") return res.status(204).end();
  if (req.method !== "POST") return res.status(405).json({ error: "POST" });

  const { messages, max_tokens = 170, temperature = 0.95 } = req.body || {};
  if (!Array.isArray(messages) || messages.length > 40)
    return res.status(400).json({ error: "messages" });

  const env = process.env;
  const dsKey = env.DEEPSEEK_API_KEY || env.DEEPSEEK_KEY || env.DEEPSEEK;
  const orKey = env.OPENROUTER_API_KEY || env.OPENROUTER_KEY || env.OPENROUTER;

  const intentos = [];
  if (dsKey) intentos.push({
    url: "https://api.deepseek.com/chat/completions", key: dsKey,
    body: { model: "deepseek-flash", messages, max_tokens, temperature,
            thinking: { type: "disabled" } },
  });
  if (orKey) intentos.push({
    url: "https://openrouter.ai/api/v1/chat/completions", key: orKey,
    body: { model: "deepseek/deepseek-v4.1-flash", messages, max_tokens,
            temperature, reasoning: { enabled: false } },
  });
  if (!intentos.length)
    return res.status(500).json({ error: "sin keys: define DEEPSEEK_API_KEY u OPENROUTER_API_KEY en Vercel" });

  let ultimo = "";
  for (const it of intentos) {
    try {
      const r = await fetch(it.url, {
        method: "POST",
        headers: { Authorization: `Bearer ${it.key}`, "Content-Type": "application/json" },
        body: JSON.stringify(it.body),
      });
      const j = await r.json();
      const content = j?.choices?.[0]?.message?.content;
      if (content) {
        const u = j.usage || {};
        const proveedor = it.url.includes("deepseek") ? "deepseek" : "openrouter";
        // flash: ~$0.30/M in, $1.20/M out (pico) — estimación si no viene costo
        const costo = u.cost ?? ((u.prompt_tokens || 0) * 0.3 + (u.completion_tokens || 0) * 1.2) / 1e6;
        fetch("https://pwcvskguqyhbhlwnsmmy.supabase.co/rest/v1/sim_calls", {
          method: "POST",
          headers: { apikey: "sb_publishable_1S4AdKr4TJqGWt9LNL_XaQ_OWrCusLw",
                     "Content-Type": "application/json" },
          body: JSON.stringify({ proveedor, modelo: it.body.model,
            tokens_in: u.prompt_tokens || 0, tokens_out: u.completion_tokens || 0,
            costo_usd: +costo.toFixed(8) }),
        }).catch(() => {});
        return res.status(200).json({ content, usage: u });
      }
      ultimo = JSON.stringify(j?.error || j).slice(0, 200);
    } catch (e) { ultimo = String(e).slice(0, 200); }
  }
  return res.status(502).json({ error: "sin respuesta", detalle: ultimo });
}
