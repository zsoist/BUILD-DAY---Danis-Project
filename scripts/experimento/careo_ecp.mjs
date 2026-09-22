/* CAREO CONTRA HUMANOS REALES.
   Le hace a los residentes sintéticos la pregunta LITERAL de la Encuesta de
   Cultura Política del DANE y guarda sus respuestas en la misma escala 1-5.
   Después `careo_ecp.py` compara esa distribución contra la de los colombianos
   de verdad (ponderada con el factor de expansión oficial).

   Usa el prompt de producción extraído del index.html vivo. Solo DeepSeek. */
import fs from "node:fs";
import path from "node:path";

const ROOT = "/Users/daniel/21 sept - Claude Build Day";
const html = fs.readFileSync(path.join(ROOT, "dashboard/sim/index.html"), "utf8");
const script = html.slice(html.indexOf("<script>") + 8, html.lastIndexOf("</script>"));

function extraer(nombre) {
  const pats = [new RegExp(`\\nfunction ${nombre}\\s*\\(`), new RegExp(`\\nconst ${nombre}\\s*=`)];
  for (const [k, re] of pats.entries()) {
    const m = script.match(re);
    if (!m) continue;
    const i = m.index + 1;
    const desde = k === 0 ? script.indexOf("{", script.indexOf("(", i)) : i;
    let prof = 0, abierto = false, q = null, esc = false;
    for (let j = desde; j < script.length; j++) {
      const c = script[j];
      if (esc) { esc = false; continue; }
      if (q) { if (c === "\\") esc = true; else if (c === q) q = null; continue; }
      if (c === '"' || c === "'" || c === "`") { q = c; continue; }
      if ("{[(".includes(c)) { prof++; abierto = true; }
      else if ("}])".includes(c)) { prof--; if (k === 0 && prof === 0) return script.slice(i, j + 1); }
      else if (k === 1 && c === ";" && prof === 0 && abierto) return script.slice(i, j + 1);
      else if (k === 1 && c === "\n" && prof === 0 && abierto) return script.slice(i, j);
    }
  }
  throw new Error(`no encontré ${nombre}`);
}

const NOMBRES = ["TEMPERAMENTOS", "LEAN", "FRANQUEZA", "ARRANQUES", "estiloDe",
  "FUNDAMENTOS", "marcoDe", "GUSTOS", "FASTIDIOS", "momentoDe", "COMPROMISO_TXT",
  "LEAN_TXT", "leanLinea", "vida", "DIALECTOS", "dialectoDe", "persona"];
const mod = new Function("OPC", NOMBRES.map(extraer).join("\n") + "\nreturn {persona};")(null);

const RES = JSON.parse(fs.readFileSync(path.join(ROOT, "dashboard/sim/residents_v2.json"), "utf8"));
const residentes = (RES.residentes || RES).filter(r => r.edad >= 18);   // universo ECP
const DOS = JSON.parse(fs.readFileSync(path.join(ROOT, "dashboard/sim/dossiers.json"), "utf8"));
const MARG = JSON.parse(fs.readFileSync(path.join(ROOT, "dashboard/sim/marginals.json"), "utf8")).departamentos;

let seed = 20260922;
const rnd = () => (seed = (seed * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff;
const N = Number(process.argv[2] || 200);
const CODIGO = process.argv[3] || "P5301";
const SALIDA = process.argv[4] || "/tmp/careo.json";

const cb = JSON.parse(fs.readFileSync(path.join(ROOT, "simcolombia/data/ecp2023_codebook.json"), "utf8"));
let pregunta = null;
(function buscar(o) {
  if (pregunta || !o || typeof o !== "object") return;
  if (Array.isArray(o)) return o.forEach(buscar);
  if (o.codigo === CODIGO) { pregunta = o; return; }
  Object.values(o).forEach(buscar);
})(cb);
if (!pregunta) throw new Error(`no encontré ${CODIGO} en el codebook`);
const TEXTO = (pregunta.texto_literal || pregunta.etiqueta).trim();
console.error(`Pregunta ECP ${CODIGO}: ${TEXTO.slice(0, 120)}…`);

const muestra = [], usados = new Set();
const pesos = Object.keys(MARG).map(c => [c, MARG[c]?.poblacion || 1]);
const tot = pesos.reduce((a, [, w]) => a + w, 0);
let g = 0;
while (muestra.length < N && g++ < N * 400) {
  let x = rnd() * tot, cod = pesos[0][0];
  for (const [c, w] of pesos) { x -= w; if (x <= 0) { cod = c; break; } }
  const pool = residentes.filter(r => r.dpto === cod && !usados.has(r.id));
  if (pool.length) { const r = pool[Math.floor(rnd() * pool.length)]; usados.add(r.id); muestra.push(r); }
}

const env = Object.fromEntries(fs.readFileSync(path.join(ROOT, ".env"), "utf8")
  .split("\n").filter(l => l.includes("=") && !l.trim().startsWith("#"))
  .map(l => [l.slice(0, l.indexOf("=")).trim(), l.slice(l.indexOf("=") + 1).trim().replace(/^["']|["']$/g, "")]));
const KEY = env.DEEPSEEK_API_KEY || env.DEEPSEEK_KEY;

async function flash(messages, max_tokens = 120) {
  for (let i = 0; i < 3; i++) {
    try {
      const r = await fetch("https://api.deepseek.com/chat/completions", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${KEY}` },
        body: JSON.stringify({ model: "deepseek-flash", messages, max_tokens,
          temperature: 1.0, reasoning_effort: "none" }),
      });
      if (r.ok) return (await r.json()).choices?.[0]?.message?.content || "";
    } catch (e) { /* reintenta */ }
    await new Promise(s => setTimeout(s, 1200 * (i + 1)));
  }
  return "";
}

/* La instrucción imita a un encuestador del DANE leyendo la tarjeta, no a un chat. */
const INSTR = "\nTe está encuestando el DANE en la puerta de tu casa. Contesta la pregunta "
  + "tal como te la leen, eligiendo UNA sola opción de la escala. Responde con el NÚMERO "
  + "y nada más (o 99 si de verdad no sabes). Sin explicaciones.";

const out = [];
const cola = [...muestra];
await Promise.all(Array.from({ length: 8 }, async () => {
  while (cola.length) {
    const r = cola.shift();
    const txt = await flash([
      { role: "system", content: mod.persona(r, DOS[r.dpto] || {}) + INSTR },
      { role: "user", content: TEXTO },
    ]);
    const m = (txt || "").match(/\b(99|[1-5])\b/);
    out.push({ id: r.id, edad: r.edad, sexo: r.sexo, dpto: r.dpto,
      educacion: r.educacion, clase: r.clase, resp: m ? Number(m[1]) : null, crudo: (txt || "").slice(0, 80) });
    process.stderr.write(".");
  }
}));
fs.writeFileSync(SALIDA, JSON.stringify({ codigo: CODIGO, pregunta: TEXTO, n: out.length,
  fecha: new Date().toISOString(), respuestas: out }, null, 1));
console.error(`\nOK — ${out.length} respuestas → ${SALIDA}`);
