// Lote de arte con gemini-3.1-flash-lite-image (el que mejor respeta la
// referencia por precio: ver scripts/escena/banco_imagen.mjs).
//   node scripts/escena/lote.mjs <carpeta_salida>
// Escribe hojas en <salida>/{poses,nuevos,utileria}/ y un manifiesto.json con
// qué id va en qué fila de qué hoja; luego recortar_poses.py / recortar.py.
import fs from "node:fs";
const OUT = process.argv[2], K = process.env.OPENROUTER_API_KEY, M = "google/gemini-3.1-flash-lite-image";
const R = new URL("./reparto/", import.meta.url);
for (const d of ["poses", "nuevos", "utileria"]) fs.mkdirSync(`${OUT}/${d}`, { recursive: true });
const json = f => JSON.parse(fs.readFileSync(f, "utf8").match(/\{[\s\S]*\}/)[0]);
const ESTILO = "HD-2D video game sprites exactly in the style of Octopath Traveler: crisp visible pixel art, clean dark outlines, detailed readable clothing, about 3 heads tall, expressive faces, contemporary Colombia 2026, respectful and dignified.";
const POSES = "Same height and scale for all, full body, facing the viewer at a slight 3/4 angle, evenly spaced with lots of empty space. In each row, left to right: (1) standing idle, (2) walking mid-stride with the LEFT leg forward and arms swinging, (3) walking mid-stride with the RIGHT leg forward and arms swinging, (4) raising the right hand up high like asking to speak, mouth open.";
const FONDO = "Background: perfectly flat solid pure magenta (#FF00FF), no floor, no shadows, no text, no labels.";
const trabajos = [];
// 1) poses de los personajes que ya existen, de a dos por hoja
const viejos = fs.readdirSync("web/gente").filter(f => /^[a-z]+_\d+\.webp$/.test(f)).map(f => f.slice(0, -5)).sort();
for (let i = 0; i < viejos.length; i += 2) {
  const par = viejos.slice(i, i + 2);
  trabajos.push({ tipo: "poses", hoja: `poses/${par.join("+")}.png`, ids: par, refs: par.map(p => `web/gente/${p}.webp`),
    prompt: `${par.length === 2 ? "Two attached pixel-art characters are the exact references" : "The attached pixel-art character is the exact reference"}: keep each one's face, hair, skin tone, clothes, colors, proportions and pixel-art style. ${par.length === 2 ? "TOP ROW: the FIRST attached character drawn 4 times; BOTTOM ROW: the SECOND attached character drawn 4 times." : "Draw it 4 times in one row."} ${POSES} ${FONDO}` });
}
// 2) personajes nuevos del reparto del enjambre, de a dos por hoja, ya con poses
for (const f of fs.readdirSync(R).filter(f => f.startsWith("reparto_"))) {
  const reg = f.slice(8, -5), P = json(new URL(f, R)).personajes;
  for (let i = 0; i < P.length; i += 2) {
    const par = P.slice(i, i + 2), ids = par.map(p => `${reg}__${p.id}`.toLowerCase().replace(/[^a-z0-9_]/g, ""));
    const txt = par.map((p, k) => `Character ${"AB"[k]} (${p.sexo === "H" ? "man" : "woman"}, ${p.edad} years old, ${p.oficio}): ${p.en}`).join(" ");
    trabajos.push({ tipo: "nuevos", hoja: `nuevos/${ids.join("+")}.png`, ids, refs: [], meta: par.map((p, k) => ({ ...p, id: ids[k], region: reg })),
      prompt: `Character sprite sheet. ${ESTILO} ${par.length === 2 ? "TOP ROW: character A drawn 4 times; BOTTOM ROW: character B drawn 4 times." : "Character A drawn 4 times in one row."} ${POSES} ${txt} ${FONDO}` });
  }
}
// 3) utilería: la mesa de cada región y 4 cosas del lugar
const U = json(new URL("utileria.json", R)).utileria;
for (const [reg, u] of Object.entries(U)) {
  trabajos.push({ tipo: "utileria", hoja: `utileria/${reg}.png`, ids: [`mesa_${reg}`, ...u.cosas.map((_, i) => `cosa_${reg}_${i}`)], refs: [],
    prompt: `Prop sprite sheet for an HD-2D video game (exactly the style of Octopath Traveler): crisp visible pixel art, clean dark outlines, warm lighting, seen from the front at a slight elevated angle. Five separate props in one row, left to right, with lots of empty space between them: ${[u.mesa, ...u.cosas].map((x, i) => `(${i + 1}) ${x}`).join(" ")} No people. ${FONDO}` });
}
fs.writeFileSync(`${OUT}/manifiesto.json`, JSON.stringify(trabajos.map(({ refs, prompt, ...t }) => t), null, 1));
let gasto = 0, hechos = 0;
async function hacer(t) {
  if (fs.existsSync(`${OUT}/${t.hoja}`)) return;
  const url = f => `data:image/${f.endsWith(".webp") ? "webp" : "png"};base64,` + fs.readFileSync(f).toString("base64");
  for (let intento = 0; intento < 3; intento++) {
    const r = await fetch("https://openrouter.ai/api/v1/chat/completions", { method: "POST",
      headers: { Authorization: "Bearer " + K, "Content-Type": "application/json" },
      body: JSON.stringify({ model: M, modalities: ["image", "text"], image_config: { aspect_ratio: "16:9" }, usage: { include: true },
        messages: [{ role: "user", content: [{ type: "text", text: t.prompt }, ...t.refs.map(f => ({ type: "image_url", image_url: { url: url(f) } }))] }] }) });
    const j = await r.json().catch(() => ({}));
    const u = j?.choices?.[0]?.message?.images?.[0]?.image_url?.url;
    if (u) { fs.writeFileSync(`${OUT}/${t.hoja}`, Buffer.from(u.split(",")[1], "base64")); gasto += +j.usage?.cost || 0; hechos++; return; }
  }
  console.log("✗", t.hoja);
}
const cola = [...trabajos];
await Promise.all(Array.from({ length: 5 }, async () => { while (cola.length) await hacer(cola.shift()); }));
console.log(`${hechos} hojas nuevas de ${trabajos.length} · $${gasto.toFixed(3)}`);
