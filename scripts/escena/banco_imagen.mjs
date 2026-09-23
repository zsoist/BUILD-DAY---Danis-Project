// Compara modelos de imagen de OpenRouter en la misma tarea (poses de un
// personaje de referencia). Guarda cada imagen y su costo real.
//   node scripts/escena/banco_imagen.mjs <referencia> <carpeta> <modelo> [<modelo> ...]
import fs from "node:fs";
const [ref, dir, ...modelos] = process.argv.slice(2);
const k = process.env.OPENROUTER_API_KEY;
const url = `data:image/${ref.endsWith(".webp") ? "webp" : "png"};base64,` + fs.readFileSync(ref).toString("base64");
const P = fs.readFileSync(new URL("./pose_prompt.txt", import.meta.url), "utf8").trim();
fs.mkdirSync(dir, { recursive: true });
async function uno(m) {
  const t0 = Date.now(), f = `${dir}/${m.replace(/\//g, "_")}.png`;
  // 1) endpoint de imágenes (estilo OpenAI) con la referencia
  let r = await fetch("https://openrouter.ai/api/v1/images", { method: "POST",
    headers: { Authorization: "Bearer " + k, "Content-Type": "application/json" },
    body: JSON.stringify({ model: m, prompt: P, input_images: [url], size: "1536x1024" }) });
  let j = await r.json().catch(() => ({}));
  let b64 = j?.data?.[0]?.b64_json, costo = j?.usage?.cost;
  if (!b64) {                       // 2) chat con salida solo imagen o imagen+texto
    for (const mod of [["image"], ["image", "text"]]) {
      r = await fetch("https://openrouter.ai/api/v1/chat/completions", { method: "POST",
        headers: { Authorization: "Bearer " + k, "Content-Type": "application/json" },
        body: JSON.stringify({ model: m, modalities: mod, image_config: { aspect_ratio: "16:9" }, usage: { include: true },
          messages: [{ role: "user", content: [{ type: "text", text: P }, { type: "image_url", image_url: { url } }] }] }) });
      j = await r.json().catch(() => ({}));
      const u = j?.choices?.[0]?.message?.images?.[0]?.image_url?.url;
      if (u) { b64 = u.split(",")[1]; costo = j?.usage?.cost; break; }
    }
  }
  if (!b64) return console.log(`${m.padEnd(42)} ✗ ${JSON.stringify(j?.error?.message || j).slice(0, 90)}`);
  fs.writeFileSync(f, Buffer.from(b64, "base64"));
  console.log(`${m.padEnd(42)} $${(+costo || 0).toFixed(4)}  ${((Date.now() - t0) / 1000).toFixed(0)}s`);
}
await Promise.all(modelos.map(uno));
