/* ABSTENCIÓN POR CONSISTENCIA DE MUESTREO.
   Variante de careo_ecp.mjs. En vez de medir UNA respuesta por residente, le
   pregunta K=3 veces la MISMA pregunta (temperature 1.0, prompt idéntico) y mide
   cuánto se contradice el propio personaje.

   El mejor score de incertidumbre barato NO es la logprob (rankea mal) sino la
   CONSISTENCIA DE MUESTREO: si un personaje dice lo mismo las tres veces está
   seguro; si se contradice, no. `incert` = 1 menos la proporción de la moda
   (0, 0.333 o 0.667 con K=3) y `disp` (desviación estándar de las 3 respuestas
   numéricas) desempata entre personajes con la misma `incert`.

   Usa el prompt de producción extraído del index.html vivo. Solo DeepSeek.
   Uso: node scripts/experimento/abstencion_gen.mjs 200 P5301 /tmp/ab.json */
import { fileURLToPath } from "node:url";
import fs from "node:fs";
import path from "node:path";

// la raíz del repo, calculada: una ruta de disco quemada solo servía en una máquina
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const html = fs.readFileSync(path.join(ROOT, "web/index.html"), "utf8");
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
  "LEAN_TXT", "leanLinea", "vida", "DIALECTOS", "dialectoDe", "ESTILOS_RESP", "estiloRespuesta", "persona"];
const mod = new Function("OPC", NOMBRES.map(extraer).join("\n") + "\nreturn {persona};")(null);

const RES = JSON.parse(fs.readFileSync(path.join(ROOT, "web/residents_v2.json"), "utf8"));
const residentes = (RES.residentes || RES).filter(r => r.edad >= 18);   // universo ECP
const DOS = JSON.parse(fs.readFileSync(path.join(ROOT, "web/dossiers.json"), "utf8"));
const MARG = JSON.parse(fs.readFileSync(path.join(ROOT, "web/marginals.json"), "utf8")).departamentos;

let seed = 20260922;
const rnd = () => (seed = (seed * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff;
const N = Number(process.argv[2] || 200);
const CODIGO = process.argv[3] || "P5301";
const SALIDA = process.argv[4] || "/tmp/ab.json";
const K = 3;   // repeticiones de la MISMA pregunta por residente (K=3 => incert en {0, 0.333, 0.667})

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

/* Dos modos.
   CATEGÓRICO: el encuestador lee la tarjeta y la persona escoge una de las cinco
   opciones (escala 1-5) — lo que hace careo_ecp.mjs.
   CONTINUO: la persona NUNCA ve las cinco opciones; da una intensidad 0-100.
   En ambos la pregunta es idéntica en las K repeticiones; solo cambia la
   temperatura (1.0) para forzar variedad de muestreo y poder medir la contradicción. */
const MODO = (process.argv[5] || "categorico").toLowerCase();
const INSTR_CAT = "\nTe está encuestando el DANE en la puerta de tu casa. Contesta la pregunta "
  + "tal como te la leen, eligiendo UNA sola opción de la escala. Responde con el NÚMERO "
  + "y nada más (o 99 si de verdad no sabes). Sin explicaciones.";
const INSTR_CON = "\nTe está encuestando el DANE en la puerta de tu casa. IGNORA cualquier lista "
  + "de opciones numeradas que traiga la pregunta: aquí te lo preguntan con un termómetro. "
  + "Responde SOLO con un número entero de 0 a 100, donde 0 es lo más negativo que podrías "
  + "sentir sobre eso y 100 lo más positivo, y 50 es que te da exactamente igual. "
  + "Contesta con el número y nada más, sin explicaciones.";
const INSTR = MODO === "continuo" ? INSTR_CON : INSTR_CAT;

// Discretiza el texto crudo según el modo; null si no hay número válido.
function parsear(txt) {
  if (MODO === "continuo") {
    const m = (txt || "").match(/\b(\d{1,3})\b/);
    const v = m ? Number(m[1]) : null;
    return v !== null && v >= 0 && v <= 100 ? v : null;
  }
  const m = (txt || "").match(/\b(99|[1-5])\b/);
  return m ? Number(m[1]) : null;
}

// Respuesta más repetida de las K; en empate gana la primera que se vio.
function calcularModa(resps) {
  const cuenta = new Map();
  let moda = null, mejor = 0;
  for (const v of resps) {
    const k = v === null ? "∅" : String(v);
    const c = (cuenta.get(k) || 0) + 1;
    cuenta.set(k, c);
    if (c > mejor) { mejor = c; moda = v; }
  }
  return { moda, incert: 1 - mejor / resps.length };
}

// Desviación estándar (poblacional) de las K respuestas numéricas; 0 si hay <2 válidas.
function desviacion(resps) {
  const nums = resps.filter(v => typeof v === "number" && Number.isFinite(v));
  if (nums.length < 2) return 0;
  const mu = nums.reduce((a, b) => a + b, 0) / nums.length;
  return Math.sqrt(nums.reduce((a, b) => a + (b - mu) ** 2, 0) / nums.length);
}

const out = [];
const cola = [...muestra];
await Promise.all(Array.from({ length: 8 }, async () => {
  while (cola.length) {
    const r = cola.shift();
    const sistema = mod.persona(r, DOS[r.dpto] || {}) + INSTR;
    const resps = [], crudos = [];
    // K veces la MISMA pregunta, mismo prompt, temperature 1.0 => solo varía el muestreo.
    for (let k = 0; k < K; k++) {
      const txt = await flash([
        { role: "system", content: sistema },
        { role: "user", content: TEXTO },
      ]);
      crudos.push((txt || "").slice(0, 80));
      resps.push(parsear(txt));
    }
    const { moda, incert } = calcularModa(resps);
    const disp = desviacion(resps);
    out.push({ id: r.id, edad: r.edad, sexo: r.sexo, dpto: r.dpto,
      educacion: r.educacion, clase: r.clase, modo: MODO,
      resps, moda, incert, disp, score: incert + disp / 10, crudos });
    process.stderr.write(".");
  }
}));

fs.writeFileSync(SALIDA, JSON.stringify({
  codigo: CODIGO, pregunta: TEXTO, k: K, n: out.length,
  fecha: new Date().toISOString(), modo: MODO, respuestas: out,
}, null, 2));

const porIncert = {};
for (const o of out) porIncert[o.incert] = (porIncert[o.incert] || 0) + 1;
console.error(`\n${out.length} residentes × K=${K}. incert: ${JSON.stringify(porIncert)}`);
console.error(`Escrito en ${SALIDA}`);
