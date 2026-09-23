// node gen.mjs <modelo> <salida.png> "<prompt>" [aspect]
import fs from "node:fs";
const [modelo, salida, prompt, aspect = "16:9"] = process.argv.slice(2);
const r = await fetch("https://openrouter.ai/api/v1/chat/completions", {
  method: "POST", headers: { Authorization: "Bearer " + process.env.OPENROUTER_API_KEY, "Content-Type": "application/json" },
  body: JSON.stringify({ model: modelo, modalities: ["image", "text"], image_config: { aspect_ratio: aspect },
    usage: { include: true }, messages: [{ role: "user", content: prompt }] }) });
const j = await r.json();
const url = j.choices?.[0]?.message?.images?.[0]?.image_url?.url;
if (!url) { console.error("sin imagen", JSON.stringify(j).slice(0, 400)); process.exit(1); }
fs.writeFileSync(salida, Buffer.from(url.split(",")[1], "base64"));
console.log(salida, "$" + (j.usage?.cost ?? "?"));
