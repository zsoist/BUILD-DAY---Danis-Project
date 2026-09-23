// node generar.mjs <modelo> <salida.png> "<prompt>" [aspect] [referencia.png|webp ...]
// Las referencias van como imágenes de entrada: sirven para pedir el MISMO
// personaje en otras poses sin que cambie de cara ni de ropa.
import fs from "node:fs";
const [modelo, salida, prompt, aspect = "16:9", ...refs] = process.argv.slice(2);
const contenido = refs.length ? [{ type: "text", text: prompt }, ...refs.map(f => ({ type: "image_url",
  image_url: { url: `data:image/${f.endsWith(".webp") ? "webp" : "png"};base64,` + fs.readFileSync(f).toString("base64") } }))] : prompt;
const r = await fetch("https://openrouter.ai/api/v1/chat/completions", {
  method: "POST", headers: { Authorization: "Bearer " + process.env.OPENROUTER_API_KEY, "Content-Type": "application/json" },
  body: JSON.stringify({ model: modelo, modalities: ["image", "text"], image_config: { aspect_ratio: aspect },
    usage: { include: true }, messages: [{ role: "user", content: contenido }] }) });
const j = await r.json();
const url = j.choices?.[0]?.message?.images?.[0]?.image_url?.url;
if (!url) { console.error("sin imagen", JSON.stringify(j).slice(0, 400)); process.exit(1); }
fs.writeFileSync(salida, Buffer.from(url.split(",")[1], "base64"));
console.log(salida, "$" + (j.usage?.cost ?? "?"));
