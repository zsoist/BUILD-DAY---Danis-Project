// Una imagen con GPT Image 2.5 (flare) por el endpoint de imágenes de OpenRouter,
// con referencia de estilo. Imprime el costo real.
//   node scripts/escena/gpt_imagen.mjs <salida.png> <prompt.txt> [referencia.webp|png ...]
// Campos que importan (probados): input_references [{type:"image_url",image_url:{url}}] (con input_images el modelo
// ignora la referencia en silencio), background:"transparent", quality:"low".
import fs from "node:fs";
const [salida, promptFile, ...refs] = process.argv.slice(2);
const k = process.env.OPENROUTER_API_KEY;
if (!k || !salida || !promptFile) { console.error("uso: gpt_imagen.mjs <salida.png> <prompt.txt> [ref ...] (con OPENROUTER_API_KEY)"); process.exit(1); }
const dataURL = f => `data:image/${f.endsWith(".webp") ? "webp" : "png"};base64,` + fs.readFileSync(f).toString("base64");
const t0 = Date.now();
const r = await fetch("https://openrouter.ai/api/v1/images", {
  method: "POST", headers: { Authorization: "Bearer " + k, "Content-Type": "application/json" },
  body: JSON.stringify({ model: process.env.MODELO || "openai/gpt-image-2.5-flare", prompt: fs.readFileSync(promptFile, "utf8").trim(),
    input_references: refs.map(f => ({ type: "image_url", image_url: { url: dataURL(f) } })), size: process.env.TAM || "1536x1024", quality: "low", background: "transparent" }),
});
const j = await r.json().catch(() => ({}));
const b64 = j?.data?.[0]?.b64_json;
if (!b64) { console.error("✗", r.status, JSON.stringify(j?.error || j).slice(0, 300)); process.exit(1); }
fs.writeFileSync(salida, Buffer.from(b64, "base64"));
console.log(`${salida}  $${(+j?.usage?.cost || 0).toFixed(4)}  ${((Date.now() - t0) / 1000).toFixed(0)}s`);
